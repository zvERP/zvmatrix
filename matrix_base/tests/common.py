"""Utilidades de test reutilizables por los módulos que dependen de matrix_base."""

import json

from ..models.matrix_notifier import QUEUE_KEY

REQUEST = "odoo.addons.matrix_base.matrix_client.requests.request"


class FakeResponse:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data or {}
        self.text = json.dumps(self._data)
        self.reason = ""

    def json(self):
        return self._data


class FakeServer:
    """Simula un homeserver: registra las llamadas y responde según reglas.

    Uso: ``with patch(REQUEST, FakeServer()) as server: ...``
    """

    def __init__(self, joined=True):
        self.calls = []
        self.joined = joined

    def __call__(self, method, url, json=None, headers=None, timeout=None):
        path = url.split("/_matrix/client/v3", 1)[1]
        self.calls.append((method, path, json, headers))
        if path == "/login":
            return FakeResponse(200, {"access_token": "tok-login", "user_id": "@odoo:hs"})
        if path == "/account/whoami":
            return FakeResponse(200, {"user_id": "@odoo:hs"})
        if path.startswith("/directory/room/"):
            return FakeResponse(200, {"room_id": "!room:hs"})
        if path.startswith("/join/"):
            self.joined = True
            return FakeResponse(200, {"room_id": "!room:hs"})
        if "/send/m.room.message/" in path:
            if not self.joined:
                return FakeResponse(403, {"errcode": "M_FORBIDDEN", "error": "not in room"})
            return FakeResponse(200, {"event_id": "$ev"})
        return FakeResponse(404, {"errcode": "M_UNRECOGNIZED"})

    def sends(self):
        return [c for c in self.calls if "/send/" in c[1]]


def broken_server(*args, **kwargs):
    return FakeResponse(500, {"errcode": "M_UNKNOWN", "error": "boom"})


class MatrixTestMixin:
    """Mixin para TransactionCase: configura la conexión y da acceso a la cola."""

    @classmethod
    def _matrix_setup_connection(cls, **params):
        params = {"homeserver": "matrix.example.org", "user": "odoo", "password": "secret", **params}
        ICP = cls.env["ir.config_parameter"].sudo()
        for key, value in params.items():
            ICP.set_param("matrix_base." + key, value)

    def _matrix_clear_queue(self):
        self.env.cr.postcommit.data.pop(QUEUE_KEY, None)

    def _matrix_queue(self):
        """Mensajes pendientes de envío (en tests el post-commit nunca se ejecuta)."""
        return list(self.env.cr.postcommit.data.get(QUEUE_KEY, []))

    def _matrix_flush(self):
        """Envía la cola como lo haría el post-commit y la vacía."""
        messages = self._matrix_queue()
        self._matrix_clear_queue()
        self.env["matrix.notifier"]._send_queue(messages)
