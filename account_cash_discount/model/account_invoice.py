# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2014 Therp BV (<http://therp.nl>).
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
import datetime
from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.tools import float_round, float_is_zero, float_compare,\
        DEFAULT_SERVER_DATE_FORMAT


class AccountInvoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
            'cash_discount_move_id': fields.many2one(
                'account.move', string='Cash discount correction move'),
            }

    def create_cash_discount_move_lines(
            self, cr, uid, ids, discount, payment_move_lines, date=None,
            post_move=True, context=None):
        '''create correction entries for invoices eligible to a cash discount,
        given by the appropriate payment.term.line
        
        :param discount: the discount
        :type discount: browse_record('payment.term.line')
        :param payment_move_lines: the payment move lines to create correction
        entries for
        :type payment_move_lines: browse_record_list('account.move.line')
        :param date: the date to post the move to
        :type date: string

        :returns: list of created account.move.lines' ids
        '''
        if date is None:
            date = datetime.datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT)

        account_move_line = self.pool.get('account.move.line')
        account_move = self.pool.get('account.move')
        precision = self.pool.get('decimal.precision').precision_get(
            cr, uid, 'Account')
        result = []
        for this in self.browse(cr, uid, ids, context=context):
            discount_move_id = account_move.create(
                    cr, uid,
                    {
                        'name': _('Cash discount for %s') % this.move_id.name,
                        'period_id': self.pool.get('account.period').find(
                            cr, uid, dt=date, context=context)[0],
                        'journal_id': this.journal_id.id,
                        'date': date,
                    },
                    context=context)

            #prepare to correct potential rounding errors
            total_debit_payment = total_credit_payment = 0
            for payment_move_line in payment_move_lines:
                total_debit_payment += payment_move_line.debit
                total_credit_payment += payment_move_line.credit
            total_debit_invoice = total_credit_invoice = 0
            #create correction entries
            total_debit_correction = total_credit_correction = 0
            for move_line in this.move_id.line_id:
                line_data = self.create_cash_discount_move_line_dict(
                    discount_move_id, move_line, discount, precision)
                line_id = account_move_line.create(cr, uid, line_data,
                                                   context=context)
                result.append(line_id)
                total_debit_correction += line_data['debit']
                total_credit_correction += line_data['credit']
                total_debit_invoice += move_line.debit
                total_credit_invoice += move_line.credit

            #add rounding error to a matching correction entry
            if not float_is_zero(
                    total_debit_correction - total_credit_correction, 
                    precision):
                error_credit = max(0, float_round(
                    total_debit_correction - total_credit_correction,
                    precision))
                error_debit = max(0, float_round(
                    total_credit_correction - total_debit_correction,
                    precision))

                for correction_line in account_move_line.browse(
                        cr, uid, result, context=context):
                    if correction_line.credit and error_credit:
                        correction_line.write(
                            {'credit': correction_line.credit + error_credit})
                        total_credit_correction += error_credit
                        error_credit = 0
                    if correction_line.debit and error_debit:
                        correction_line.write(
                            {'debit': correction_line.debit + error_debit})
                        total_debit_correction += error_debit
                        error_debit = 0
                    if not error_credit and not error_debit:
                        break

            #write off differences within deviation margin
            writeoff_debit = total_debit_correction + total_debit_payment\
                    - total_debit_invoice
            writeoff_credit = total_credit_correction + total_credit_payment\
                    - total_credit_invoice

            if float_compare(writeoff_debit, writeoff_credit, precision) == 0\
               and float_compare(abs(writeoff_debit),
                                 discount.allowed_deviation,
                                 precision) == -1:
                line_id = account_move_line.create(
                    cr, uid,
                    {
                        'name': _('Cash discount writeoff'),
                        'debit': abs(writeoff_debit),
                        'move_id': discount_move_id,
                        'partner_id': this.partner_id.id,
                        'account_id': this.account_id.id
                            if writeoff_debit > 0
                            else discount.discount_expense_account_id.id,
                    },
                    context=context)
                result.append(line_id)

                line_id = account_move_line.create(
                    cr, uid,
                    {
                        'name': _('Cash discount writeoff'),
                        'credit': abs(writeoff_credit),
                        'move_id': discount_move_id,
                        'partner_id': this.partner_id.id,
                        'account_id': this.account_id.id
                            if writeoff_credit < 0
                            else discount.discount_income_account_id.id,
                    },
                    context=context)
                result.append(line_id)

            this.write({'cash_discount_move_id': discount_move_id})
            if post_move:
                account_move.post(cr, uid, [discount_move_id], context=context)
        return result

    def create_cash_discount_move_line_dict(self, move_id, move_line,
                                            discount, precision):
        '''return a dict suitable to create a correction entry for specified
        cash discount
        
        :param move_id: the move to append correction entries to
        :type move: int
        :param move_line: the move to append correction entries to
        :type move_line: browse_record('account.move')
        :param discount: the discount
        :type discount: browse_record('payment.term.line')

        :returns: dict that can be fed to account_move_line.create
        '''

        account_id = move_line.account_id.id
        if move_line.account_id.id in [
                l.account_id.id for l in move_line.invoice.invoice_line]:
            if move_line.credit:
                account_id = discount.discount_expense_account_id.id\
                        or account_id
            if move_line.debit:
                account_id = discount.discount_income_account_id.id\
                        or account_id

        data = self.pool.get('account.move.line').copy_data(
            move_line._cr, move_line._uid, move_line.id,
            default={
                'name': _('Cash discount for %s') % move_line.name,
                'debit': float_round(
                    move_line.credit * discount.discount / 100,
                    precision),
                'credit': float_round(
                    move_line.debit * discount.discount / 100,
                    precision),
                'tax_amount': float_round(
                    -move_line.tax_amount * discount.discount / 100,
                    precision),
                'amount_currency': float_round(
                    -move_line.amount_currency * discount.discount / 100,
                    precision),
                'move_id': move_id,
                'account_id': account_id,
            },
            context=move_line._context)
        return data

    def copy_data(self, cr, uid, id, default=None, context=None):
        '''reset cash_discount_move_id'''
        if default is None:
            default = {}
        default.setdefault('cash_discount_move_id', False)

        return super(AccountInvoice, self).copy_data(
            cr, uid, id, default=default, context=None)

    def get_matching_cash_discount(self, cr, uid, ids, amount, 
                                   payment_date=None, context=None):
        '''return a cash discount that matches the amount paid and payment
        date'''
        result = False
        for this in self.browse(cr, uid, ids, context=context):
            if not this.payment_term or\
                    not this.payment_term.cash_discount_ids:
                continue
            for discount in this.payment_term.cash_discount_ids:
                if discount.matches(amount, this.date_invoice,
                                    this.amount_total,
                                    payment_date=payment_date):
                    return discount
        return result

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None,
                        description=None, journal_id=None, context=None):
        result = super(AccountInvoice, self)._prepare_refund(
            cr, uid, invoice, date=date, period_id=period_id,
            description=description, journal_id=journal_id, context=context)
        if invoice.cash_discount_move_id:
            result['payment_term'] = False
            for discount_move in invoice.cash_discount_move_id.line_id:
                if not discount_move.account_id == invoice.account_id:
                    continue
                result['invoice_line'].append(
                    (0, 0,
                     {
                         'name': discount_move.name,
                         'account_id': discount_move.account_id.id,
                         'price_unit': -(discount_move.credit or
                                         -discount_move.debit),
                     }))

        return result
