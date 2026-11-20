import logging

from odoo import SUPERUSER_ID, _, api, models

from ..matrix_client import MatrixClient, MatrixError

_logger = logging.getLogger(__name__)

PARAM_PREFIX = "matrix_base."
QUEUE_KEY = "matrix_base.queue"


class MatrixNotifier(models.AbstractModel):
    """Punto de entrada para que otros módulos envíen mensajes a Matrix.

    Uso típico desde otro módulo::

        self.env["matrix.notifier"].send_after_commit(
            "#sala:servidor", "texto plano", html="<b>texto</b>", record=self
        )

    El contexto ``matrix_notify_disable=True`` desactiva los envíos.
    """

    _name = "matrix.notifier"
    _description = "Envío de mensajes a Matrix"

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------
    @api.model
    def _get_client(self):
        """Cliente construido a partir de la configuración global."""
        ICP = self.env["ir.config_parameter"].sudo()
        token = ICP.get_param(PARAM_PREFIX + "access_token") or ICP.get_param(
            PARAM_PREFIX + "session_token"
        )
        return MatrixClient(
            ICP.get_param(PARAM_PREFIX + "homeserver"),
            access_token=token,
            user=ICP.get_param(PARAM_PREFIX + "user"),
            password=ICP.get_param(PARAM_PREFIX + "password"),
        )

    @api.model
    def _store_session(self, client):
        """Guarda el token obtenido con usuario/contraseña para reutilizarlo
        (evita crear un dispositivo nuevo en Matrix en cada envío)."""
        if client.logged_in:
            self.env["ir.config_parameter"].sudo().set_param(
                PARAM_PREFIX + "session_token", client.access_token
            )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    @api.model
    def send(self, room, body, html=None, msgtype="m.text"):
        """Envío inmediato. Lanza ``MatrixError`` si falla."""
        client = self._get_client()
        try:
            return client.send_message(room, body, html=html, msgtype=msgtype)
        finally:
            self._store_session(client)

    @api.model
    def send_after_commit(self, room, body, html=None, msgtype="m.text", record=None):
        """Encola el mensaje y lo envía cuando la transacción se confirma.

        Si la transacción se revierte, no se envía nada. Un fallo de Matrix
        nunca afecta a la operación que generó el mensaje: se registra en el
        log y, si ``record`` tiene chatter, se deja una nota en él.
        """
        if self.env.context.get("matrix_notify_disable") or not room:
            return
        postcommit = self.env.cr.postcommit
        queue = postcommit.data.setdefault(QUEUE_KEY, [])
        first = not queue
        queue.append(
            {
                "room": room,
                "body": body,
                "html": html,
                "msgtype": msgtype,
                "model": record._name if record else None,
                "res_id": record.id if record else None,
            }
        )
        if not first:
            return  # ya hay un callback registrado en esta transacción

        registry = self.env.registry
        lang = self.env.lang

        @postcommit.add
        def _matrix_flush():
            messages = postcommit.data.pop(QUEUE_KEY, [])
            try:
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {"lang": lang})
                    env["matrix.notifier"]._send_queue(messages)
            except Exception:
                _logger.exception("Matrix: error enviando %s mensaje(s)", len(messages))

    # ------------------------------------------------------------------
    # Interno
    # ------------------------------------------------------------------
    @api.model
    def _send_queue(self, messages):
        if not messages:
            return
        try:
            client = self._get_client()
        except MatrixError as e:
            _logger.warning("Matrix: configuración incompleta: %s", e)
            return
        try:
            for msg in messages:
                try:
                    client.send_message(
                        msg["room"], msg["body"], html=msg["html"], msgtype=msg["msgtype"]
                    )
                except MatrixError as e:
                    self._on_send_error(msg, e)
        finally:
            self._store_session(client)

    @api.model
    def _on_send_error(self, msg, error):
        _logger.warning("Matrix: no se pudo enviar a %s: %s", msg["room"], error)
        if not (msg["model"] and msg["res_id"]):
            return
        record = self.env[msg["model"]].browse(msg["res_id"]).exists()
        if record and hasattr(record, "message_post"):
            record.message_post(
                body=_("No se pudo enviar la notificación a Matrix: %s", error),
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
