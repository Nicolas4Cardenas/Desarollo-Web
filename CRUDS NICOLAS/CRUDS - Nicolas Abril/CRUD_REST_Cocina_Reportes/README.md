# 🍽️ Polirestaurante — CRUD como servicio REST de Nicolas (Flask + Postman)

Servicio REST en **Flask** para **cocina, reportes e historial** (**HU-06, 07, 08, 13, 14 y 15**), consumido desde **Postman**.
Igual que el CRUD de Juan, se conecta a MySQL llamando a los procedimientos almacenados del backend
(`sp_cocina_*`, `sp_admin_*`), así las reglas de negocio (roles, estados, transacciones) siguen viviendo en la base de datos.

| HU | Funcionalidad | Método y ruta | Rol |
|---|---|---|---|
| HU-06 | Ver cola de pedidos pendientes | `GET /api/v1/cocina/cola` | COCINA |
| HU-07 | Ver pedidos en preparación | `GET /api/v1/cocina/en-preparacion` | COCINA |
| HU-07 | Iniciar preparación (PENDIENTE → EN_PREPARACION) | `PUT /api/v1/cocina/pedidos/{id}/preparar` | COCINA |
| HU-08 | Marcar listo (EN_PREPARACION → LISTO) | `PUT /api/v1/cocina/pedidos/{id}/listo` | COCINA |
| HU-13 | Reporte de ventas (filtros por categoría y producto) | `GET /api/v1/reportes/ventas?desde=&hasta=` | ADMIN |
| HU-14 | Reporte de tiempos de preparación | `GET /api/v1/reportes/tiempos?desde=&hasta=` | ADMIN |
| HU-15 | **Read** listar historial (todo o de un pedido) | `GET /api/v1/historial[?id_pedido=]` | ADMIN |
| HU-15 | **Read** ver un registro | `GET /api/v1/historial/{id}` | ADMIN |
| HU-15 | **Create** crear registro | `POST /api/v1/historial` | ADMIN |
| HU-15 | **Update** editar estado / fecha / usuario | `PUT /api/v1/historial/{id}` | ADMIN |
| HU-15 | **Delete** eliminar registro | `DELETE /api/v1/historial/{id}` | ADMIN |

### Rutas de apoyo (HU de otros, para que mi parte funcione completa)

Permiten armar la demo desde Postman sin tocar Workbench. Los reportes solo cuentan pedidos **ENTREGADOS**, por eso hace falta poder crear, entregar y consultar pedidos.

| Ruta | Qué hace | Rol |
|---|---|---|
| `GET /api/v1/salud` | Estado del servicio | — |
| `GET /api/v1/menu`, `GET /api/v1/mesas/libres` | Menú y mesas libres | MESERO |
| `POST /api/v1/pedidos` | HU-01 Crear pedido | MESERO |
| `POST /api/v1/pedidos/{id}/productos` | HU-02 Agregar producto | MESERO |
| `PUT /api/v1/pedidos/{id}/entregar` | HU-04 Marcar entregado | MESERO |
| `DELETE /api/v1/pedidos/{id}` | HU-05 Cancelar pedido | MESERO |
| `GET /api/v1/pedidos[?estado=]`, `GET /api/v1/pedidos/{id}` | Ver todos los pedidos / uno con sus productos | ADMIN |

## 📁 Estructura

```text
CRUD_REST_Cocina_Reportes/
├── app.py                      # punto de entrada
├── config.py                   # configuración desde .env
├── api/
│   ├── __init__.py             # fábrica de la app Flask
│   ├── rutas/                  # capa REST: cocina.py, reportes.py, historial.py, apoyo.py
│   ├── dao/                    # capa de datos: CALL a los procedimientos almacenados
│   ├── db.py                   # conexión a MySQL
│   ├── auth.py                 # identificación del usuario (cabecera X-Usuario-Id)
│   ├── validaciones.py         # validación de entrada (enteros, estados, fechas)
│   └── errores.py              # errores de BD -> códigos HTTP
├── postman/                    # colección de Postman lista para importar
├── tests/test_api.py           # 28 pruebas automáticas (pytest)
├── requirements.txt
└── .env.example
```

Arquitectura por capas (RNF-08): **rutas → DAO → procedimientos almacenados (MySQL)**.

## 🗄️ Base de datos local

Este CRUD usa una **copia local** del backend en la base `poli_restaurante_nicolas`, para no tocar la del grupo.
El script está en `../sql/backend_nicolas.sql` y se diferencia del oficial en cuatro cosas:

1. Crea la base `poli_restaurante_nicolas` (no hace `DROP` de `poli_restaurante`).
2. **Se quitaron los triggers** `trg_historial_no_update` y `trg_historial_no_delete`, para que el historial se pueda editar y eliminar (HU-15).
3. **El administrador puede ejecutar cualquier operación**: `sp_validar_rol` acepta ADMINISTRADOR en cualquier rol, y una función nueva `fn_es_admin` le permite operar pedidos de otros meseros.
4. Se añadieron procedimientos nuevos: `sp_admin_listar_historial`, `sp_admin_ver_historial`, `sp_admin_crear_historial`, `sp_admin_editar_historial`, `sp_admin_eliminar_historial`, `sp_admin_listar_pedidos` y `sp_admin_ver_pedido`.

Para cargarlo: abrir `backend_nicolas.sql` en MySQL Workbench y ejecutarlo completo (⚡), o desde consola:
`mysql -u root -p < sql/backend_nicolas.sql`. Cuando quieras dejar la base limpia, vuelve a ejecutarlo.

## ▶️ Cómo ejecutarlo

Requisitos: Python 3.10+, MySQL 8 con `backend_nicolas.sql` ya ejecutado.

```bash
pip install -r requirements.txt
copy .env.example .env      # Windows (en Linux/Mac: cp) y edita usuario/contraseña de MySQL
python app.py               # http://localhost:5000/api/v1
```

Prueba rápida: abrir `http://localhost:5000/api/v1/salud` en el navegador.

## 🔐 Identificación del usuario

Cada petición (excepto `/salud`) envía la cabecera `X-Usuario-Id`. La base valida el rol:

| Usuario | id | Rol | Lo usa |
|---|---|---|---|
| admin | 1 | ADMINISTRADOR | HU-13, 14, 15 |
| mesero1 | 2 | MESERO | rutas de apoyo |
| cocina1 | 4 | COCINA | HU-06, 07, 08 |

**El administrador puede usar TODAS las rutas** (cocina y mesero, incluso sobre pedidos de otros meseros). Los demás roles solo las suyas:
un mesero o un cocinero que llame una ruta de otro rol recibe `403 ACCESO_DENEGADO`.

(El login con JWT corresponde a HU-16 y no hace parte de este CRUD.)

## 📮 Usar Postman

1. Importar `postman/Polirestaurante_REST_Nicolas.postman_collection.json`.
2. Con la API corriendo, ejecutar las carpetas **en orden** (o *Run collection*): crea un pedido, lo lleva por
   cocina hasta LISTO, lo entrega, consulta los reportes y termina con el CRUD de historial.
3. El `id_pedido` y el `id_historial` se guardan solos en las variables de la colección.
4. Se puede repetir la colección completa: al entregar el pedido la mesa vuelve a quedar libre.

## 📬 Ejemplos

**HU-06 — Ver cola** · `GET /api/v1/cocina/cola` (`X-Usuario-Id: 4`) · `200 OK`
```json
{ "total": 1, "pedidos": [ { "id_pedido": 1, "fecha_creacion": "2026-10-25 12:00:00", "mesas": [1],
    "productos": [ { "producto": "Hamburguesa clásica", "cantidad": 2, "notas": "sin cebolla" } ] } ] }
```

**HU-07 — Preparar** · `PUT /api/v1/cocina/pedidos/1/preparar` (sin cuerpo) · `200 OK`
```json
{ "mensaje": "Pedido en preparación", "id_pedido": 1, "estado": "EN_PREPARACION" }
```

**HU-13 — Ventas** · `GET /api/v1/reportes/ventas?desde=2026-10-01&hasta=2026-10-31&id_categoria=2` (`X-Usuario-Id: 1`)
```json
{ "desde": "2026-10-01", "hasta": "2026-10-31",
  "resumen": { "pedidos_entregados": 1, "productos_vendidos": 2, "total_ventas": 44000.0 },
  "por_categoria": [ { "categoria": "Platos fuertes", "productos_vendidos": 2, "total_ventas": 44000.0 } ],
  "por_producto": [ { "producto": "Hamburguesa clásica", "categoria": "Platos fuertes", "unidades_vendidas": 2, "total_ventas": 44000.0 } ] }
```

**HU-15 — Crear** · `POST /api/v1/historial` · `201 Created` (`fecha` e `id_usuario_cambio` son opcionales)
```json
{ "id_pedido": 1, "estado": "LISTO", "fecha": "2026-10-25 12:30:00", "id_usuario_cambio": 4 }
```
**HU-15 — Editar** · `PUT /api/v1/historial/7` · lo que no se envía se conserva
```json
{ "estado": "CANCELADO" }
```
**HU-15 — Eliminar** · `DELETE /api/v1/historial/7` (sin cuerpo) · `200 OK`

## ⚠️ Errores

Formato: `{ "error": "mensaje", "codigo": "CODIGO" }`

| HTTP | Códigos |
|---|---|
| 400 | `JSON_INVALIDO`, `CAMPO_REQUERIDO`, `CAMPO_INVALIDO`, `ESTADO_INVALIDO`, `FECHA_INVALIDA`, `RANGO_INVALIDO`, `CANTIDAD_INVALIDA` |
| 401 | `NO_AUTENTICADO` (falta `X-Usuario-Id`) |
| 403 | `ACCESO_DENEGADO` (rol incorrecto) |
| 404 | `PEDIDO_NO_EXISTE`, `HISTORIAL_NO_EXISTE`, `USUARIO_NO_EXISTE`, `MESA_NO_EXISTE`, `PRODUCTO_NO_EXISTE` |
| 409 | `TRANSICION_INVALIDA`, `PEDIDO_VACIO`, `MESA_OCUPADA`, `PEDIDO_BLOQUEADO`, `PRODUCTO_NO_DISPONIBLE`, `CANCELACION_NO_PERMITIDA` |
| 503 | `BD_NO_DISPONIBLE` |

## ✅ Pruebas automáticas

Con MySQL levantado y el `.env` configurado:

```bash
pytest -v
```

28 pruebas con casos felices y de error de las 6 HU (cola sin pedidos vacíos, preparar dos veces, listo sin preparar,
ventas que suman un pedido entregado, rangos de fecha inválidos, CRUD completo de historial, roles incorrectos...).
Crean pedidos reales: al terminar quedan ENTREGADOS o CANCELADOS y las mesas libres. Para dejar la base limpia, vuelve a ejecutar `backend_nicolas.sql`.

## 📝 Nota sobre el backend

`sp_cocina_iniciar_preparacion` rechaza pedidos sin productos (`PEDIDO_VACIO`) y `sp_cambiar_estado` solo permite avanzar
en orden (PENDIENTE → EN_PREPARACION → LISTO → ENTREGADO). Editar el historial **no** cambia el estado del pedido: solo
modifica el registro de auditoría (y, por lo tanto, lo que calculan los reportes).
