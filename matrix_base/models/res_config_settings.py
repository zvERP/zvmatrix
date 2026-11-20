from odoo import _, fields, models
from odoo.exceptions import UserError

from ..matrix_client import MatrixClient, MatrixError
from .matrix_notifier import PARAM_PREFIX


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    matrix_homeserver = fields.Char(
        string="Servidor Matrix",
        config_parameter=PARAM_PREFIX + "homeserver",
        help="URL del homeserver, p. ej. https://matrix.example.org",
    )
    matrix_access_token = fields.Char(
        string="Access token",
        config_parameter=PARAM_PREFIX + "access_token",
        help="Si se indica, tiene prioridad sobre usuario/contraseña.",
    )
    matrix_user = fields.Char(
        string="Usuario Matrix",
        config_parameter=PARAM_PREFIX + "user",
        help="@usuario:servidor.org o solo el nombre local.",
    )
    matrix_password = fields.Char(
        string="Contraseña Matrix",
        config_parameter=PARAM_PREFIX + "password",
    )

    def set_values(self):
        ICP = self.env["ir.config_parameter"].sudo()
        old = {
            key: ICP.get_param(PARAM_PREFIX + key) or False
            for key in ("homeserver", "user", "password")
        }
        super().set_values()
        new = {
            "homeserver": self.matrix_homeserver or False,
            "user": self.matrix_user or False,
            "password": self.matrix_password or False,
        }
        if old != new:
            # Las credenciales han cambiado: el token de sesión cacheado ya no vale.
            ICP.set_param(PARAM_PREFIX + "session_token", False)

    def _matrix_client_from_settings(self):
        """Cliente con los valores del formulario (aunque aún no se hayan guardado)."""
        self.ensure_one()
        return MatrixClient(
            self.matrix_homeserver,
            access_token=self.matrix_access_token,
            user=self.matrix_user,
            password=self.matrix_password,
        )

    def _matrix_notification(self, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Matrix"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_matrix_test_connection(self):
        try:
            user_id = self._matrix_client_from_settings().whoami()
        except MatrixError as e:
            raise UserError(_("No se pudo conectar con Matrix:\n%s", e)) from e
        return self._matrix_notification(_("Conexión correcta como %s.", user_id))
