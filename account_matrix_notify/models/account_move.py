from html import escape

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted._matrix_notify_posted()
        return posted

    def _matrix_notify_posted(self):
        Notifier = self.env["matrix.notifier"]
        for move in self:
            company = move.company_id
            if (
                move.state == "posted"
                and company.matrix_notify_enabled
                and company.matrix_room
                and move.move_type in company._matrix_notify_move_types()
            ):
                body, html = move._matrix_message()
                Notifier.send_after_commit(company.matrix_room, body, html, record=move)

    # ------------------------------------------------------------------
    # Contenido del mensaje
    # ------------------------------------------------------------------
    def _matrix_sale_orders(self):
        """Pedidos de venta vinculados (si ``sale`` está instalado) o, si no, el origen."""
        self.ensure_one()
        lines = self.invoice_line_ids
        if "sale_line_ids" in lines._fields:
            orders = lines.sale_line_ids.order_id
            if orders:
                return ", ".join(orders.mapped("name"))
        return self.invoice_origin or ""

    def _matrix_projects(self):
        """Cuentas analíticas (proyectos) de la distribución analítica de las líneas."""
        self.ensure_one()
        account_ids = []
        for line in self.invoice_line_ids:
            for key in line.analytic_distribution or {}:
                for account_id in str(key).split(","):
                    if account_id.isdigit() and int(account_id) not in account_ids:
                        account_ids.append(int(account_id))
        accounts = self.env["account.analytic.account"].browse(account_ids).exists()
        return ", ".join(accounts.mapped("display_name"))

    def _matrix_message_lines(self):
        """Líneas del mensaje, en orden. Sobrescribir para personalizar.

        Las líneas vacías se omiten.
        """
        self.ensure_one()
        return [
            self.partner_id.commercial_partner_id.display_name or "",
            self.name,
            self._matrix_sale_orders(),
            self._matrix_projects(),
        ]

    def _matrix_url(self):
        self.ensure_one()
        return "{}/web#id={}&model=account.move&view_type=form".format(
            self.get_base_url(), self.id
        )

    def _matrix_message(self):
        """Devuelve (texto plano, HTML). En HTML el número enlaza a la factura."""
        self.ensure_one()
        lines = [line for line in self._matrix_message_lines() if line]
        body = "\n".join(lines)
        link = '<a href="{}">{}</a>'.format(escape(self._matrix_url()), escape(self.name))
        html = "<br/>".join(
            link if line == self.name else escape(line) for line in lines
        )
        return body, html
