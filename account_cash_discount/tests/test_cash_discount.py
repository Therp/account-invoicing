# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Therp BV (<http://therp.nl>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime
from openerp.tests.common import SingleTransactionCase
from openerp import netsvc


class TestCashDiscount(SingleTransactionCase):
    def assert_invoice_state(self, expected):
        """
        Check that the state of our invoices is
        equal to the 'expected' parameter
        """
        invoice = self.registry('account.invoice').read(
            self.cr, self.uid, self.invoice_id, ['state'])
        assert invoice['state'] == expected, \
            'Invoice does not go into state \'%s\'' % expected

    def setup_company(self, reg, cr, uid):
        """
        Set up a company and configure the
        current user to work with that company
        """
        data_model = reg('ir.model.data')
        self.country_id = data_model.get_object_reference(
            cr, uid, 'base', 'nl')[1]
        self.currency_id = data_model.get_object_reference(
            cr, uid, 'base', 'EUR')[1]
        self.company_id = reg('res.company').create(
            cr, uid,
            {
                'name': '_cash_discount_test_company',
                'currency_id': self.currency_id,
                'country_id': self.country_id,
            })
        self.partner_id = reg('res.company').read(
            cr, uid, self.company_id, ['partner_id'])['partner_id'][0]
        reg('res.users').write(
            cr, uid, [uid],
            {'company_ids': [(4, self.company_id)]})
        reg('res.users').write(
            cr, uid, [uid],
            {'company_id': self.company_id})

    def setup_chart(self, reg, cr, uid):
        """
        Set up the configurable chart of accounts and create periods
        """
        data_model = reg('ir.model.data')
        chart_setup_model = reg('wizard.multi.charts.accounts')
        chart_template_id = data_model.get_object_reference(
            cr, uid, 'account', 'configurable_chart_template')[1]
        chart_values = {
            'company_id': self.company_id,
            'currency_id': self.currency_id,
            'chart_template_id': chart_template_id
        }
        chart_values.update(
            chart_setup_model.onchange_chart_template_id(
                cr, uid, [], 1)['value'])
        chart_setup_id = chart_setup_model.create(
            cr, uid, chart_values)
        chart_setup_model.execute(
            cr, uid, [chart_setup_id])
        ac_ids = reg('account.account').search(
            cr, uid, [('company_id', '=', self.company_id)])
        year = datetime.now().strftime('%Y')
        fiscalyear_id = reg('account.fiscalyear').create(
            cr, uid,
            {
                'name': year,
                'code': year,
                'company_id': self.company_id,
                'date_start': '%s-01-01' % year,
                'date_stop': '%s-12-31' % year,
            })
        reg('account.fiscalyear').create_period(
            cr, uid, [fiscalyear_id])

    def setup_receivables(self, reg, cr, uid, context=None):
        """
        Set up suppliers and invoice them. Check that the invoices
        can be validated properly.
        """
        partner_model = reg('res.partner')
        self.customer_id = partner_model.create(
            cr, uid, {
                'name': 'Customer',
                'customer': True,
                'country_id': self.country_id,
                }, context=context)
        self.receivable_id = reg('account.account').search(
            cr, uid, [
                ('company_id', '=', self.company_id),
                ('code', '=', '110200')])[0]
        income_id = reg('account.account').search(
            cr, uid, [
                ('company_id', '=', self.company_id),
                ('code', '=', '200000')])[0]

        payment_term_id = reg('account.payment.term').create(
            cr, uid, {
                'name': 'Cash discount',
                'line_ids': [(0, False, {})],
                'cash_discount_ids': [(0, False, {
                    'days': 2,
                    'discount': 0.10,
                    'allowed_deviation': 0.2,
                    'discount_income_account_id': income_id,
                    })],
                })

        invoice_model = reg('account.invoice')
        values = {
            'type': 'out_invoice',
            'partner_id': self.customer_id,
            'account_id': self.receivable_id,
            'payment_term': payment_term_id,
            'invoice_line': [
                (
                    0,
                    False,
                    {
                        'name': 'Sales 1',
                        'price_unit': 100.0,
                        'quantity': 1,
                        'account_id': income_id,
                    }
                )
            ],
        }
        self.invoice_id = invoice_model.create(
            cr, uid, values,
            context={
                'type': 'out_invoice',
            })
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(
            uid, 'account.invoice', self.invoice_id, 'invoice_open', cr)
        self.assert_invoice_state('open')

    def setup_voucher(self, reg, cr, uid):
        # Based on account_voucher/test/sales_payment
        voucher_reg = reg('account.voucher')
        vals = {}
        journal_id = reg('account.journal').search(
            cr, uid, [('company_id', '=', self.company_id),
                      ('code', '=', 'BNK2')])[0]
        res = voucher_reg.onchange_partner_id(
            cr, uid, [], self.customer_id, journal_id,
            0.0, 1, ttype='receipt', date=False)

        account_view_id = reg('account.account').search(
            cr, uid, [
                ('company_id', '=', self.company_id),
                ('code', '=', '1104')])[0]
        user_type_cash_id = reg('ir.model.data').get_object_reference(
            cr, uid, 'account', 'data_account_type_cash')[1]
        account_cash_id = reg('account.account').create(
            cr, uid, {
                'name': 'Cash',
                'code': '110499',
                'company_id': self.company_id,
                'parent_id': account_view_id,
                'type': 'liquidity',
                'user_type': user_type_cash_id,
                })
        period_id = self.registry('account.invoice').read(
            self.cr, self.uid, self.invoice_id, ['period_id'])['period_id'][0]
        vals = {
            'period_id': period_id,
            'account_id': account_cash_id,
            'amount': 90.0,
            'company_id': self.company_id,
            'journal_id': journal_id,
            'partner_id': self.customer_id,
            'type': 'receipt',
            }
        if not res['value']['line_cr_ids']:
            res['value']['line_cr_ids'] = [
                {'type': 'cr', 'account_id': self.receivable_id}]
        # Remove values for fields that are readonly in the field
        del(res['value']['line_cr_ids'][0]['date_original'])
        del(res['value']['line_cr_ids'][0]['date_due'])
        res['value']['line_cr_ids'][0]['amount'] = 90.0
        vals['line_cr_ids'] = [(0, 0, i) for i in res['value']['line_cr_ids']]
        voucher_id = voucher_reg.create(cr, uid, vals)
        voucher = voucher_reg.browse(cr, uid, voucher_id)
        assert (voucher.state == 'draft'), "Voucher is not in draft state"
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(
            uid, 'account.voucher', voucher.id, 'proforma_voucher', cr)
        self.assert_invoice_state('paid')

    def test_cash_discount(self):
        reg, cr, uid, = self.registry, self.cr, self.uid
        self.setup_company(reg, cr, uid)
        self.setup_chart(reg, cr, uid)
        self.setup_receivables(reg, cr, uid)
        self.setup_voucher(reg, cr, uid)
