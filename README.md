# zvmatrix

Módulos Odoo 16 de integración con Matrix (salas sin cifrar).

| Módulo | Descripción |
|---|---|
| [matrix_base](matrix_base/) | Conexión con Matrix y `matrix.notifier.send_after_commit()` para otros módulos. |
| [account_matrix_notify](account_matrix_notify/) | Avisa en una sala al validar facturas. |

## CI / runboat

Estructura OCA 16.0 (`setup/<addon>` con setuptools-odoo): se instala con
`oca_install_addons` en las imágenes `ghcr.io/oca/oca-ci/py3.10-odoo16.0`.
Los tests corren en GitHub Actions (`.github/workflows/test.yml`) sobre la rama `16.0`.
