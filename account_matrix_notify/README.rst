==================================
Notificación de facturas en Matrix
==================================

Envía un mensaje a una sala de Matrix cada vez que se valida una factura.
Depende de ``matrix_base`` (la conexión se configura allí).

Mensaje
=======

::

    facturado                                         ← tipo (facturado, rectificativa…)
    SO1407                                            ← pedido(s) de venta vinculados
    INV/2026/0222                                     ← número de factura
    FEV - GRC Xunta 2026_Touro - Concello de Touro    ← cuenta(s) analítica(s)

* Pedido: de las líneas de venta vinculadas si ``sale`` está instalado; si no, el *Origen*.
* Proyecto: cuentas analíticas de la distribución analítica de las líneas, con su
  nombre completo (``nombre - cliente``). Si no hay, se muestra el cliente.
* Texto plano, sin enlace: así los clientes de Matrix no generan vista previa.
* Si hay varios se separan por comas; las líneas vacías se omiten.
* Personalizable sobrescribiendo ``account.move._matrix_message_lines()``.

Configuración
=============

*Contabilidad › Configuración › Ajustes › Matrix*, por empresa:

* **Notificar facturas en Matrix** y **Sala**.
* Tipos: facturas de cliente (por defecto), rectificativas de cliente,
  facturas y rectificativas de proveedor.
* Botón **Enviar mensaje de prueba a la sala**.

Si se pasa a borrador y se vuelve a validar, se notifica otra vez.
