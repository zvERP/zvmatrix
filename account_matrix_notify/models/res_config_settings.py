from odoo import _, fields, models
from odoo.exceptions import UserError

from odoo.addons.matrix_base.matrix_client import MatrixError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    matrix_notify_enabled = fields.Boolean(
        related="company_id.matrix_notify_enabled", readonly=False
    )
    matrix_room = fields.Char(related="company_id.matrix_room", readonly=False)
    matrix_notify_out_invoice = fields.Boolean(
        related="company_id.matrix_notify_out_invoice", readonly=False
    )
    matrix_notify_out_refund = fields.Boolean(
        related="company_id.matrix_notify_out_refund", readonly=False
    )
    matrix_notify_in_invoice = fields.Boolean(
        related="company_id.matrix_notify_in_invoice", readonly=False
    )
    matrix_notify_in_refund = fields.Boolean(
        related="company_id.matrix_notify_in_refund", readonly=False
    )

    def action_matrix_test_invoice_room(self):
        self.ensure_one()
        try:
            self._matrix_client_from_settings().send_message(
                self.matrix_room,
                _("✅ Mensaje de prueba desde Odoo (%s).", self.company_id.name),
            )
        except MatrixError as e:
            raise UserError(_("No se pudo enviar el mensaje a Matrix:\n%s", e)) from e
        return self._matrix_notification(_("Mensaje enviado a %s.", self.matrix_room))
