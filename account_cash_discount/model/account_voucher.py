# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2012-2012 Camptocamp Austria (<http://www.camptocamp.at>)
#    Copyright (C) 2014 Therp BV (<http://www.therp.nl>)
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

from openerp.osv import fields, orm


class AccountVoucher(orm.Model):
    _inherit = 'account.voucher'

    def voucher_move_line_create(
            self, cr, uid, voucher_id, line_total, move_id, company_currency,
            current_currency, context=None):
        total, ids_list = super(AccountVoucher, self).voucher_move_line_create(
                cr, uid, voucher_id, line_total, move_id, company_currency,
                current_currency)
        '''add correction entries to payment if the payment amount matches a
        cash discount amount and is in time for that'''

        account_move_line = self.pool.get('account.move.line')

        precision = self.pool.get('decimal.precision').precision_get(
                cr, uid, 'Account')
        voucher = self.browse(cr, uid, voucher_id, context=context)
        move = self.pool.get('account.move').browse(
                cr, uid, move_id, context=context)

        for ids in ids_list:
            move_lines = account_move_line.browse(cr, uid, ids, 
                                                  context=context)
            for move_line in move_lines:
                #only act on move liness with invoices whose payment term is a
                #cash discount
                if move_line.invoice and move_line.invoice.payment_term and\
                        move_line.invoice.payment_term.cash_discount_ids:

                    #find a cash discount that matches current payment
                    discount = move_line.invoice.get_matching_cash_discount(
                        voucher.amount, payment_date=voucher.date)
                    if not discount:
                        continue

                    discount_move_line_ids = move_line.invoice\
                            .create_cash_discount_move_lines(
                                payment_move_lines=move.line_id,
                                discount=discount, date=move.date)

                    #put correction entries into list with matching
                    #original ones to have them reconciled at once
                    for discount_move_line in account_move_line.browse(
                            cr, uid, discount_move_line_ids, context=context):
                        if discount_move_line.account_id == \
                                move_line.account_id:
                            ids.append(discount_move_line.id)

        return total, ids_list
