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
from openerp.osv.orm import Model
from openerp.osv import fields

class AccountMoveLineReconcile(Model):
    _inherit = 'account.move.line.reconcile'

    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        'invoice_has_cash_discount': fields.boolean('Cash discount on invoice')
    }

    def default_get(self, cr, uid, fields, context=None):
        result = super(AccountMoveLineReconcile, self).default_get(
            cr, uid, fields, context=context)
        for move_line in self.pool.get('account.move.line').browse(
                cr, uid, context.get('active_ids', []), context=context):
            if move_line.invoice:
                if move_line.invoice.id != result.get('invoice_id'):
                    result['invoice_id'] = move_line.invoice.id
                    result['invoice_has_cash_discount'] = bool(
                        move_line.invoice.get_matching_cash_discount(
                            result.get('credit')) or
                        move_line.invoice.get_matching_cash_discount(
                            result.get('debit')))
                else:
                    result['invoice_id'] = False
                    result['invoice_has_cash_discount'] = False
        return result

    def reconcile_with_cash_discount(self, cr, uid, ids, context=None):
        account_move_line = self.pool.get('account.move.line')
        for this in self.browse(cr, uid, ids, context=context):
            discount = this.invoice_id.get_matching_cash_discount(this.credit)\
                    or this.invoice_id.get_matching_cash_discount(this.debit)
            if not discount:
                continue
            payment_move_lines = [
                l for ml in account_move_line.browse(
                        cr, uid, context.get('active_ids', []),
                    context=context)
                  for l in ml.move_id.line_id
                if not l.invoice]
            correction_move_line_ids = this.invoice_id\
                    .create_cash_discount_move_lines(discount,
                                                     payment_move_lines)
            reconcile_ids = context.get('active_ids', [])
            for correction_move_line in account_move_line.browse(
                    cr, uid, correction_move_line_ids, context=context):
                for payment_move_line in payment_move_lines:
                    if payment_move_line.account_id ==\
                            correction_move_line.account_id:
                        reconcile_ids.append(correction_move_line.id)
                        break
            return self.trans_rec_reconcile_full(
                cr, uid, [this.id], dict(context, active_ids=reconcile_ids))
        pass
