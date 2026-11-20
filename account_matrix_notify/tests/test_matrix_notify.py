from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.matrix_base.tests.common import (
    REQUEST,
    FakeServer,
    MatrixTestMixin,
    broken_server,
)


@tagged("post_install", "-at_install")
class TestMatrixNotify(MatrixTestMixin, AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls._matrix_setup_connection(access_token="tok")
        cls.company_data["company"].write(
            {"matrix_notify_enabled": True, "matrix_room": "#facturas:hs"}
        )
        plan = cls.env["account.analytic.plan"].create({"name": "Proyectos"})
        cls.analytic = cls.env["account.analytic.account"].create(
            {
                "name": "FEV - GRC Xunta 2026_Touro",
                "plan_id": plan.id,
                "partner_id": cls.partner_a.id,
            }
        )

    def setUp(self):
        super().setUp()
        self._matrix_clear_queue()

    def _invoice(self, move_type="out_invoice", analytic=True):
        invoice = self.init_invoice(move_type, amounts=[100.0])
        invoice.invoice_origin = "SO1407"
        if analytic:
            invoice.invoice_line_ids.analytic_distribution = {str(self.analytic.id): 100}
        return invoice

    def test_message_format(self):
        invoice = self._invoice()
        invoice.action_post()
        queue = self._matrix_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["room"], "#facturas:hs")
        self.assertEqual(
            queue[0]["body"].split("\n"),
            [
                self.partner_a.name,
                invoice.name,
                "SO1407",
                "FEV - GRC Xunta 2026_Touro - %s" % self.partner_a.name,
            ],
        )
        self.assertIn('<a href="', queue[0]["html"])
        self.assertIn("model=account.move", queue[0]["html"])

    def test_empty_lines_skipped(self):
        invoice = self._invoice(analytic=False)
        invoice.invoice_origin = False
        invoice.action_post()
        self.assertEqual(
            self._matrix_queue()[0]["body"].split("\n"), [self.partner_a.name, invoice.name]
        )

    def test_move_types(self):
        (self._invoice("out_invoice") + self._invoice("in_invoice")).action_post()
        self.assertEqual(len(self._matrix_queue()), 1)  # proveedor desactivado
        self._matrix_clear_queue()
        self.company_data["company"].matrix_notify_in_invoice = True
        self._invoice("in_invoice").action_post()
        self.assertEqual(len(self._matrix_queue()), 1)

    def test_disabled(self):
        self.company_data["company"].matrix_notify_enabled = False
        self._invoice().action_post()
        self.assertFalse(self._matrix_queue())

    def test_send_and_failure_note(self):
        invoice = self._invoice()
        invoice.action_post()
        server = FakeServer()
        with patch(REQUEST, server):
            self._matrix_flush()
        self.assertEqual(len(server.sends()), 1)
        self.assertEqual(server.sends()[0][3]["Authorization"], "Bearer tok")

        invoice2 = self._invoice()
        invoice2.action_post()
        with patch(REQUEST, broken_server):
            self._matrix_flush()
        self.assertIn("boom", invoice2.message_ids[0].body)
