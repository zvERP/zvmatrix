from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    matrix_notify_enabled = fields.Boolean(string="Notificar facturas en Matrix")
    matrix_room = fields.Char(
        string="Sala de Matrix",
        help="ID de la sala (!abc123:servidor.org) o alias (#facturas:servidor.org). "
        "El usuario de Matrix debe estar en la sala o tener una invitación pendiente.",
    )
    matrix_notify_out_invoice = fields.Boolean(string="Facturas de cliente", default=True)
    matrix_notify_out_refund = fields.Boolean(string="Rectificativas de cliente")
    matrix_notify_in_invoice = fields.Boolean(string="Facturas de proveedor")
    matrix_notify_in_refund = fields.Boolean(string="Rectificativas de proveedor")

    def _matrix_notify_move_types(self):
        self.ensure_one()
        return {
            move_type
            for move_type in ("out_invoice", "out_refund", "in_invoice", "in_refund")
            if self[f"matrix_notify_{move_type}"]
        }
