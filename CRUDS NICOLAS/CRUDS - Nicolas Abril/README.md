# CRUDS — Nicolas (Polirestaurante)

HU asignadas: **HU-06 Ver cola · HU-07 En preparación · HU-08 Listo · HU-13 Reporte de ventas · HU-14 Reporte de tiempos · HU-15 Historial**.
El historial tiene CRUD completo (crear, ver, editar, eliminar); cocina cambia estados; los reportes consultan.

```text
CRUDS - Nicolas Abril/
├── sql/backend_nicolas.sql          # base local poli_restaurante_nicolas (ejecutar primero)
├── CRUD_REST_Cocina_Reportes/       # servicio REST (Flask) + colección de Postman
├── CRUD_Driver_MySQL/               # consola con mysql-connector (SQL a mano)
└── CRUD_ORM_SQLAlchemy/             # consola con SQLAlchemy (ORM)
```

## Pasos para la demostración

1. Abrir `sql/backend_nicolas.sql` en MySQL Workbench y ejecutarlo completo (⚡). Crea la base **poli_restaurante_nicolas**, sin tocar la del grupo.
2. En la carpeta del proyecto que se va a mostrar: `pip install -r requirements.txt`, copiar `.env.example` a `.env` y poner la contraseña de MySQL.
3. REST: `python app.py` e importar la colección de `CRUD_REST_Cocina_Reportes/postman/`. Driver y ORM: `python main.py`.

## Qué cambia respecto al backend del grupo (`backend.sql`)

- Base con otro nombre: no hace `DROP DATABASE poli_restaurante`.
- Se quitaron los triggers `trg_historial_no_update` y `trg_historial_no_delete`, para poder editar y eliminar el historial.
- El **administrador puede ejecutar cualquier operación** (cocina y mesero, incluso en pedidos de otros meseros): se modificó `sp_validar_rol` y se agregó `fn_es_admin`.
- Procedimientos nuevos: `sp_admin_listar_historial`, `sp_admin_ver_historial`, `sp_admin_crear_historial`, `sp_admin_editar_historial`,
  `sp_admin_eliminar_historial`, `sp_admin_listar_pedidos`, `sp_admin_ver_pedido`.
- Las HU de otros (crear pedido, agregar producto, entregar, cancelar) están incluidas como apoyo, para que los reportes tengan datos.
