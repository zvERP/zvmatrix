=============
Matrix (base)
=============

Conexión con un servidor Matrix y envío de mensajes a salas **sin cifrar**.
No envía nada por sí mismo: es la base para módulos de notificaciones.

Configuración
=============

*Ajustes › Ajustes generales › Integraciones › Matrix* (solo administradores):

* **Servidor Matrix**: ``https://matrix.example.org``
* **Access token**, o bien **usuario** y **contraseña**. Con usuario/contraseña se hace
  login una vez y se reutiliza el token (se descarta si cambian las credenciales).
* Botón **Probar conexión**.

El usuario de Matrix debe estar en la sala o tener invitación pendiente (si recibe
``M_FORBIDDEN`` intenta unirse). Se admiten IDs (``!abc:servidor``) y alias (``#sala:servidor``).

Uso desde otro módulo
=====================

.. code-block:: python

    self.env["matrix.notifier"].send_after_commit(
        "#sala:servidor", "texto plano", html="<b>texto</b>", record=self
    )

* Se envía **tras el commit**: si la transacción se revierte, no se envía nada.
* Un fallo de Matrix nunca rompe la operación: se registra en el log y, si ``record``
  tiene chatter, se deja una nota.
* ``matrix.notifier.send()`` envía en el momento y lanza ``MatrixError`` si falla.
* Contexto ``matrix_notify_disable=True`` para desactivar envíos (importaciones, etc.).
* Para tests: ``odoo.addons.matrix_base.tests.common`` (servidor simulado y ``MatrixTestMixin``).
