# Copyright 2022 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountProductMoveItemLine(models.Model):
    _name = "account.product.move.item.line"
    _description = "Items for journal entry for given products"

    debit = fields.Monetary(default=0.0)
    credit = fields.Monetary(default=0.0)
    account_id = fields.Many2one(
        comodel_name="account.account", ondelete="cascade", required=True
    )
    currency_id = fields.Many2one(related="product_move_id.currency_id")
    product_move_id = fields.Many2one(comodel_name="account.product.move")
