# Copyright 2022 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAccountMoveJournalTemplate(TransactionCase):
    def setUp(self):
        super().setUp()
        self.item_lines = self.env["account.move.journal.template.item.line"]
        # demo journal entry template
        self.template = self.env.ref(
            "account_move_journal_template.account_move_journal_template_01"
        )
        # demo account.journals
        self.journal = self.env["account.journal"].create(
            {"name": "demo_journal", "type": "sale", "code": "code"}
        )
        self.another_journal = self.env["account.journal"].create(
            {"name": "another_demo_journal", "type": "sale", "code": "code"}
        )
        # a random demo account
        self.account = self.env["account.account"].search([], limit=1)
        # demo journal item lines for journal entry template
        self.item_line_01 = self.item_lines.create(
            {
                "journal_id": self.journal.id,
                "account_id": self.account.id,
                "journal_template_id": self.template.id,
                "credit": 1.0,
            }
        )
        self.item_line_02 = self.item_lines.create(
            {
                "journal_id": self.journal.id,
                "account_id": self.account.id,
                "journal_template_id": self.template.id,
                "debit": 1.0,
            }
        )
        self.item_line_03 = self.item_lines.create(
            {
                "journal_id": self.another_journal.id,
                "account_id": self.account.id,
                "journal_template_id": self.template.id,
                "credit": 1.0,
            }
        )
        self.item_line_04 = self.item_lines.create(
            {
                "journal_id": self.another_journal.id,
                "account_id": self.account.id,
                "journal_template_id": self.template.id,
                "debit": 1.0,
            }
        )
        # demo invoice
        self.invoice = self.env["account.move"].create(
            {
                "type": "out_invoice",
                "date": fields.Date.today(),
                "partner_id": self.env["res.partner"]
                .search([("customer_rank", ">", 0)], limit=1)
                .id,
                "line_ids": [
                    (
                        0,
                        None,
                        {
                            "product_id": self.template.product_tmpl_line_ids[0]
                            .product_tmpl_id.product_variant_ids[0]
                            .id,
                            "quantity": 300.0,
                            "account_id": self.account.id,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "product_id": self.template.product_tmpl_line_ids[1]
                            .product_tmpl_id.product_variant_ids[0]
                            .id,
                            "quantity": 600.0,
                            "account_id": self.account.id,
                        },
                    ),
                ],
            }
        )

    def test_debit_credit_balance(self):
        """Check that balance is always 0 for template"""
        line = self.item_lines.create(
            {
                "journal_id": self.journal.id,
                "journal_template_id": self.template.id,
                "credit": 1.0,
                "account_id": self.account.id,
            }
        )
        with self.assertRaises(UserError):
            self.template._check_balanced()
        line.write({"credit": 0.0})
        self.template._check_balanced()

    def test_active(self):
        self.template.toggle_active()
        self.assertFalse(self.template.active)

    def test_workflow(self):
        # Post the invoice
        self.invoice.action_post()
        # Journal entries created
        self.assertTrue(self.invoice.journal_entry_ids)
        # Action returns these only
        self.assertEqual(
            self.invoice.journal_entry_ids,
            self.invoice.search(self.invoice.action_view_journal_entries()["domain"]),
        )
        # Product templates are the same
        self.assertEqual(
            self.invoice.mapped("line_ids.product_id.product_tmpl_id"),
            self.template.product_tmpl_line_ids.mapped("product_tmpl_id"),
        )
        # Journals are the same
        self.assertEqual(
            self.invoice.mapped("journal_entry_ids.journal_id"),
            self.template.journal_item_ids.mapped("journal_id"),
        )
        # Set invoice to draft
        self.invoice.button_draft()
        # See that all journal entries are in draft
        for this in self.invoice.journal_entry_ids:
            self.assertEqual(this.state, "draft")
        # Post again...
        self.invoice.action_post()
        # ...only to cancel right away
        self.invoice.button_cancel()
        for this in self.invoice.journal_entry_ids:
            self.assertEqual(this.state, "cancel")