# Copyright 2022 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, fields, models


class AccountProductMoveProductLine(models.Model):
    _name = "account.product.move.product.line"
    _description = "Lines for product configuration"

    _sql_constraints = [
        (
            "product_tmpl_id",
            "UNIQUE (product_tmpl_id)",
            _("Line for this product already exists"),
        ),
    ]

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template", string="Product",
    )
    default_code = fields.Char(related="product_tmpl_id.default_code", readonly=True)
    product_move_id = fields.Many2one(comodel_name="account.product.move")

    def name_get(self):
        names = []
        for this in self:
            names.append(
                (
                    this.id,
                    "%s" % this.product_tmpl_id.name
                    + " - "
                    + (this.product_tmpl_id.default_code or ""),
                )
            )
        return names
