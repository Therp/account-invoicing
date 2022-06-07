# Copyright 2022 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import _, api, fields, models
from odoo.tools import UserError


class AccountProductMove(models.Model):
    _name = "account.product.move"
    _description = "Template for additional journal entries/items"

    name = fields.Char(required=True, copy=False, default="New")
    product_tmpl_line_ids = fields.One2many(
        comodel_name="account.product.move.product.line",
        inverse_name="product_move_id",
        string="Product lines",
        help="Journal items will be created for these products",
    )
    journal_item_ids = fields.One2many(
        comodel_name="account.product.move.item.line",
        inverse_name="product_move_id",
        copy=True,
        string="Journal Items",
        help="Journal items to be added in new journal entry",
    )
    active = fields.Boolean(default=True)

    def action_toggle_active(self):
        self.ensure_one()
        self.active = not self.active

    def _check_balanced(self):
        """ An adaptation of account.move._check_balanced()"""
        moves = self.filtered(lambda move: move.journal_item_ids)
        if not moves:
            return
        self.env["account.product.move.item.line"].flush(
            self.env["account.product.move.item.line"]._fields
        )
        self._cr.execute(
            """
            SELECT
                line.product_move_id,
                ROUND(SUM(line.debit - line.credit),
                currency.decimal_places)
            FROM account_product_move_item_line line
            JOIN account_product_move move ON
                move.id = line.product_move_id
            JOIN account_journal journal ON
                journal.id = line.journal_id
            JOIN res_company company ON
                company.id = journal.company_id
            JOIN res_currency currency ON
                currency.id = company.currency_id
            WHERE
                line.product_move_id IN %s
            GROUP BY line.product_move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        """,
            [tuple(self.ids)],
        )

        query_res = self._cr.fetchall()
        if query_res:
            ids = [res[0] for res in query_res]
            sums = [res[1] for res in query_res]
            raise UserError(
                _(
                    "Cannot create unbalanced journal entry. "
                    "Ids: %s\nDifferences debit - credit: %s"
                )
                % (ids, sums)
            )

    # TODO: take care that previous products have no product_move connected to them
    def write(self, vals):
        res = super().write(vals)
        for this in self:
            this._check_balanced()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_balanced()
        return records
