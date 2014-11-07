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
from openerp.osv.orm import Model
from openerp.osv import fields
from openerp.tools import float_compare, DEFAULT_SERVER_DATE_FORMAT

class AccountPaymentTermCashDiscount(Model):
    _name = 'account.payment.term.cash.discount'
    _description= 'Cash discount'
    _rec_name = 'days'
    _order = 'days'

    _columns = {
        'payment_term_id': fields.many2one(
            'account.payment.term', 'Payment term', required=True),
        'days': fields.integer('Days', required=True),
        'discount': fields.float('Discount', required=True),
        'allowed_deviation': fields.float(
            'Allowed deviation',
            help="The amount a payment can deviate from the computed amount "
            "and still be accepted as payment within this discount.\n"
            "Think of rounding errors as use case for this"),
        'discount_income_account_id': fields.many2one(
            'account.account', string='Discount Income Account',
            help="This account will be used to post the cash discount income"),
        'discount_expense_account_id': fields.many2one(
            'account.account',
            string='Discount Expense Account',
            help="This account will be used to post the cash discount expense")
    }

    def matches(self, cr, uid, ids, amount, invoice_date, invoice_amount,
                payment_date=None, context=None):
        '''determine if an amount paid at a certain date matches an invoiced
        amount from a certain date
        
        :param amount: the amount paid
        :type amount: float
        :param invoice_date: the invoice's date
        :type invoice_date: string
        :param invoice_amount: the invoiced amount
        :type invoice_amount: float
        :param payment_date: the date of payment, today if None
        :type payment_date: string        
        '''
        precision = self.pool.get('decimal.precision').precision_get(
            cr, uid, 'Account')

        if not payment_date:
            payment_date = datetime.datetime.now().strftime(
                DEFAULT_SERVER_DATE_FORMAT)

        for this in self.browse(cr, uid, ids, context=context):
            date = (
                datetime.datetime.strptime(
                    invoice_date, DEFAULT_SERVER_DATE_FORMAT) +
                datetime.timedelta(days=this.days))\
                .strftime(DEFAULT_SERVER_DATE_FORMAT)

            return date >= payment_date and float_compare(
                amount,
                (1 - this.discount / 100) * invoice_amount
                    - this.allowed_deviation,
                precision) == 1 and float_compare(
                amount,
                (1 - this.discount / 100) * invoice_amount
                    + this.allowed_deviation,
                precision) == -1
