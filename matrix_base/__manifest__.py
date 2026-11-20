{
    "name": "Matrix (base)",
    "version": "16.0.1.0.0",
    "category": "Hidden/Tools",
    "summary": "Conexión con Matrix y envío de mensajes a salas sin cifrar. "
    "Base para módulos de notificaciones.",
    "author": "zvERP.com",
    "website": "https://www.zverp.com",
    "license": "AGPL-3",
    "depends": ["base_setup"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
