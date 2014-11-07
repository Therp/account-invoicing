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
        print reg('account.account').read(cr, uid, ac_ids, ['code'])
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
        customer_id = partner_model.create(
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
            'partner_id': customer_id,
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

    def test_cash_discount(self):
        reg, cr, uid, = self.registry, self.cr, self.uid
        self.setup_company(reg, cr, uid)
        self.setup_chart(reg, cr, uid)
        self.setup_receivables(reg, cr, uid)
