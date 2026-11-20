"""Cliente mínimo de la API Client-Server de Matrix (salas sin cifrar)."""

import logging
import uuid
from urllib.parse import quote

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class MatrixError(Exception):
    def __init__(self, message, errcode=None, status=None):
        super().__init__(message)
        self.errcode = errcode
        self.status = status

    def __str__(self):
        msg = super().__str__()
        if self.errcode:
            msg = f"{self.errcode}: {msg}"
        if self.status:
            msg = f"[HTTP {self.status}] {msg}"
        return msg


class MatrixClient:
    """Autenticación por access token o por usuario/contraseña.

    Si se usa usuario/contraseña, tras ``login()`` el token obtenido queda en
    ``self.access_token`` para que el llamador pueda cachearlo y no crear un
    dispositivo nuevo en cada envío.
    """

    def __init__(self, homeserver, access_token=None, user=None, password=None,
                 timeout=DEFAULT_TIMEOUT):
        if not homeserver:
            raise MatrixError("No se ha configurado el servidor (homeserver) de Matrix.")
        homeserver = homeserver.strip().rstrip("/")
        if not homeserver.startswith(("http://", "https://")):
            homeserver = "https://" + homeserver
        self.homeserver = homeserver
        self.access_token = access_token or None
        self.user = user or None
        self.password = password or None
        self.timeout = timeout
        self.logged_in = False

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------
    def _request(self, method, path, payload=None, auth=True):
        url = f"{self.homeserver}/_matrix/client/v3{path}"
        headers = {}
        if auth:
            headers["Authorization"] = f"Bearer {self.access_token}"
        try:
            resp = requests.request(
                method, url, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.RequestException as e:
            raise MatrixError(f"Error de conexión con {self.homeserver}: {e}") from e
        try:
            data = resp.json()
        except ValueError:
            data = {}
        if resp.status_code >= 400:
            raise MatrixError(
                data.get("error") or (resp.text or resp.reason or "")[:300],
                errcode=data.get("errcode"),
                status=resp.status_code,
            )
        return data

    def _authed(self, method, path, payload=None):
        self.ensure_token()
        try:
            return self._request(method, path, payload)
        except MatrixError as e:
            # Token caducado/invalidado: si tenemos credenciales, reintentamos.
            if e.errcode == "M_UNKNOWN_TOKEN" and self.user and self.password and not self.logged_in:
                self.login()
                return self._request(method, path, payload)
            raise

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def login(self):
        if not (self.user and self.password):
            raise MatrixError("Faltan usuario y/o contraseña de Matrix.")
        data = self._request(
            "POST",
            "/login",
            {
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": self.user},
                "password": self.password,
                "initial_device_display_name": "Odoo",
            },
            auth=False,
        )
        self.access_token = data["access_token"]
        self.logged_in = True
        return self.access_token

    def ensure_token(self):
        if not self.access_token:
            if not (self.user and self.password):
                raise MatrixError(
                    "No hay access token ni usuario/contraseña configurados para Matrix."
                )
            self.login()

    def whoami(self):
        return self._authed("GET", "/account/whoami").get("user_id")

    def resolve_room(self, room):
        """Devuelve el room_id (!xxx:server) a partir de un ID o alias (#sala:server)."""
        room = (room or "").strip()
        if not room:
            raise MatrixError("No se ha configurado la sala de Matrix.")
        if room.startswith("#"):
            return self._authed("GET", f"/directory/room/{quote(room, safe='')}")["room_id"]
        return room

    def join(self, room):
        return self._authed("POST", f"/join/{quote(room, safe='')}", {})["room_id"]

    def send_message(self, room, body, html=None, msgtype="m.text"):
        room_id = self.resolve_room(room)
        content = {"msgtype": msgtype, "body": body}
        if html:
            content["format"] = "org.matrix.custom.html"
            content["formatted_body"] = html

        def _send():
            path = "/rooms/{}/send/m.room.message/{}".format(
                quote(room_id, safe=""), uuid.uuid4().hex
            )
            return self._authed("PUT", path, content)

        try:
            return _send()
        except MatrixError as e:
            # El usuario no está en la sala: intentamos unirnos (funciona si
            # la sala es pública o el usuario tiene invitación pendiente).
            if e.errcode == "M_FORBIDDEN":
                _logger.info("Matrix: uniéndose a la sala %s", room)
                self.join(room)
                return _send()
            raise
