from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..matrix_client import MatrixClient
from .common import REQUEST, FakeServer, MatrixTestMixin, broken_server


@tagged("post_install", "-at_install")
class TestMatrixBase(MatrixTestMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._matrix_setup_connection()

    def setUp(self):
        super().setUp()
        self._matrix_clear_queue()

    def test_client_login_and_join(self):
        server = FakeServer(joined=False)
        client = MatrixClient("matrix.example.org", user="odoo", password="secret")
        with patch(REQUEST, server):
            client.send_message("#facturas:hs", "hola")
        paths = [c[1] for c in server.calls]
        self.assertEqual(paths[0], "/login")
        self.assertTrue(paths[1].startswith("/directory/room/%23facturas"))
        self.assertTrue(any(p.startswith("/join/") for p in paths))
        self.assertEqual(len(server.sends()), 2)  # 403 + reintento tras unirse
        self.assertEqual(server.sends()[-1][3]["Authorization"], "Bearer tok-login")
        self.assertEqual(client.homeserver, "https://matrix.example.org")

    def test_send_after_commit_queues_and_caches_token(self):
        notifier = self.env["matrix.notifier"]
        notifier.send_after_commit("!room:hs", "uno")
        notifier.send_after_commit("!room:hs", "dos", html="<b>dos</b>")
        self.assertEqual([m["body"] for m in self._matrix_queue()], ["uno", "dos"])
        server = FakeServer()
        with patch(REQUEST, server):
            self._matrix_flush()
        self.assertEqual([s[2]["body"] for s in server.sends()], ["uno", "dos"])
        self.assertEqual(server.sends()[1][2]["formatted_body"], "<b>dos</b>")
        self.assertEqual([c[1] for c in server.calls].count("/login"), 1)
        self.assertEqual(
            self.env["ir.config_parameter"].sudo().get_param("matrix_base.session_token"),
            "tok-login",
        )

    def test_disabled_by_context(self):
        self.env["matrix.notifier"].with_context(matrix_notify_disable=True).send_after_commit(
            "!room:hs", "nada"
        )
        self.assertFalse(self._matrix_queue())

    def test_errors_never_raise(self):
        partner = self.env["res.partner"].create({"name": "Sin chatter quizá"})
        self.env["matrix.notifier"].send_after_commit("!room:hs", "x", record=partner)
        with patch(REQUEST, broken_server):
            self._matrix_flush()  # no debe lanzar excepción

    def test_settings_clear_session_on_credentials_change(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("matrix_base.session_token", "viejo")
        settings = self.env["res.config.settings"].create({})
        settings.execute()
        self.assertEqual(ICP.get_param("matrix_base.session_token"), "viejo")
        settings = self.env["res.config.settings"].create({"matrix_user": "otro"})
        settings.execute()
        self.assertFalse(ICP.get_param("matrix_base.session_token"))
