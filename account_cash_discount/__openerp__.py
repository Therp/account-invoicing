# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 Camptocamp Austria (<http://www.camptocamp.at>)
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


{
    'name': 'Cash discount',
    'version': '0.9',
    'category': 'Accounting & Finance',
    'description': """
Cash Discount (Austria and Germany style)
=========================================

Usage
-----

Define your discounts as part of your payment terms. Keep in mind that other
computation lines than 'balance' won't make much sense, so only fill in one
computation line of type 'balance' indicating your payment date.

When paying your invoice, fill in the exact amount for the discounted invoice.
If the payment date and the amount matches a discount, the invoice will be
marked as paid and some correction move lines will be created to reflect the
invoice being paid with a discount.

If you manually reconcile move lines, you'll be offered a button to book the
writeoff amount as cash discount if a matching cash discount can be found.
    
Example
-------

On 01/20/2014, you charged EUR 80 to a customer, with 25% tax, totalling in
EUR 100. Further, you set up a payment term for this invoice that includes
5% discount if paid within a week.

If you fill in EUR 95 and payment date 01/22/2014 when paying the invoice, the
following happens:

- the invoice is marked as paid
- on the invoice's 'Other info' tag, you'll find a field 'Cash discount
  correction' with the following lines:

    - EUR 1 as debit on your tax account
    - EUR 4 as debit on your income account
    - EUR 5 as credit on your customer's account

TODO
----

- cash discounts don't show up on invoice report
- multi currency not tested
- no automatic reconciliation
""",
    'author': 'Therp BV',
    'depends': [ 'account_voucher' ],
    'data': [
        'view/account_move_line_reconcile.xml',
        'view/account_payment_term.xml',
        'view/account_invoice.xml',
        'security/ir.model.access.csv',
           ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
