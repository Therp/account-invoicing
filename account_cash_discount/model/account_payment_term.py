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
from openerp.tools.translate import _


class AccountPaymentTerm(orm.Model):
    _inherit = "account.payment.term"
    _columns = {
        'cash_discount_ids': fields.one2many(
            'account.payment.term.cash.discount', 'payment_term_id',
            'Cash discount'),
    }

    def _check_validity(self, cr, uid, ids, context=None):
        for this in self.browse(
                cr, uid, ids if isinstance(ids, list) else [ids],
                context=context):
            if not this.cash_discount_ids:
                continue
            for payment_term_line in this.line_ids:
                if payment_term_line.value == 'balance':
                    continue
                raise orm.except_orm(
                    _('Error'), _('When working with cash discounts, you can '
                                  'only have one computation line of type '
                                  '"balance"!'))

    def create(self, cr, uid, vals, context=None):
        result = super(AccountPaymentTerm, self).create(
            cr, uid, vals, context=context)
        self._check_validity(cr, uid, result, context=context)
        return result

    def write(self, cr, uid, ids, vals, context=None):
        result = super(AccountPaymentTerm, self).write(
            cr, uid, ids, vals, context=context)
        self._check_validity(cr, uid, ids, context=context)
        return result
