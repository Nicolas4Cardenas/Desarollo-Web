# 🍽️ Polirestaurante — CRUD como servicio REST (Flask + Postman)

Servicio REST en **Flask** para el módulo del mesero (**HU-01 a HU-05**), consumido desde **Postman**.
Se conecta al backend MySQL del proyecto (`backend.sql`) llamando a sus procedimientos almacenados, de modo que
las reglas de negocio (estados, roles, transacciones, historial inmutable) siguen viviendo en la base de datos.

| HU | Funcionalidad | Método y ruta |
|---|---|---|
| HU-01 | Crear pedido | `POST /api/v1/pedidos` |
| HU-02 | Agregar productos | `POST /api/v1/pedidos/{id}/productos` |
| HU-03 | Editar producto del pedido | `PUT /api/v1/pedidos/{id}/productos/{id_detalle}` |
| HU-03 | Quitar producto del pedido | `DELETE /api/v1/pedidos/{id}/productos/{id_detalle}` |
| HU-04 | Marcar como entregado | `PUT /api/v1/pedidos/{id}/entregar` |
| HU-05 | Cancelar pedido | `DELETE /api/v1/pedidos/{id}` |
| Read | Ver / listar pedidos, menú, mesas libres | `GET /pedidos`, `/pedidos/{id}`, `/menu`, `/mesas/libres` |

## 📁 Estructura

```text
CRUD_REST_Pedidos/
├── app.py                      # punto de entrada
├── config.py                   # configuración desde .env
├── api/
│   ├── __init__.py             # fábrica de la app Flask
│   ├── rutas/pedidos.py        # capa REST: endpoints (HU-01..05)
│   ├── dao/pedido_dao.py       # capa de datos: CALL a los procedimientos almacenados
│   ├── db.py                   # conexión a MySQL
│   ├── auth.py                 # identificación del usuario (cabecera X-Usuario-Id)
│   ├── validaciones.py         # validación de entrada
│   └── errores.py              # errores de BD -> códigos HTTP
├── postman/                    # colección de Postman lista para importar
├── tests/test_pedidos.py       # 21 pruebas automáticas (pytest)
├── requirements.txt
└── .env.example
```

Arquitectura por capas (RNF-08): **rutas → DAO → procedimientos almacenados (MySQL)**.

## ▶️ Cómo ejecutarlo

Requisitos: Python 3.10+, MySQL 8 con `backend.sql` ya ejecutado (base `poli_restaurante`).

```bash
pip install -r requirements.txt
cp .env.example .env        # en Windows: copy .env.example .env  -> y edita usuario/contraseña de MySQL
python app.py               # http://localhost:5000/api/v1
```

Prueba rápida: abrir `http://localhost:5000/api/v1/salud` en el navegador.

## 🔐 Identificación del usuario

El `backend.sql` recibe el id del usuario en cada procedimiento y valida el **rol dentro de la base de datos**.
Por eso cada petición (excepto `/salud`) envía la cabecera:

```text
X-Usuario-Id: 2
```

Usuarios de los datos semilla: `1` admin · `2` mesero1 · `3` mesero2 · `4` cocina1.
(El login con JWT corresponde a HU-16 y no hace parte de este CRUD.)

## 📮 Usar Postman

1. Importar `postman/Polirestaurante_REST.postman_collection.json`.
2. Con la API corriendo, ejecutar las carpetas **en orden** (o *Run collection*).
   El id del pedido y del detalle se guardan solos en las variables de la colección.
3. En la carpeta **HU-04** hay un **paso manual**: para que el pedido pase a `LISTO` lo debe mover cocina.
   Ejecutar en MySQL Workbench (con el `id_pedido` que muestran las variables):

   ```sql
   CALL sp_cocina_iniciar_preparacion(4, 1);
   CALL sp_cocina_marcar_listo(4, 1);
   ```

## 📬 Ejemplos

**HU-01 — Crear pedido** · `POST /api/v1/pedidos` · `201 Created`
```json
{ "id_mesa": 1 }
```
```json
{ "mensaje": "Pedido creado en estado PENDIENTE",
  "pedido": { "id_pedido": 1, "estado": "PENDIENTE", "mesas": [1], "total": 0.0, "productos": [] } }
```

**HU-02 — Agregar producto** · `POST /api/v1/pedidos/1/productos` · `201 Created`
```json
{ "id_producto": 3, "cantidad": 2, "notas": "sin cebolla" }
```
```json
{ "mensaje": "Producto agregado al pedido (si ya estaba, se sumó la cantidad)",
  "id_pedido": 1, "total": 44000.0, "id_detalle": 1 }
```

**HU-03 — Editar** · `PUT /api/v1/pedidos/1/productos/1` · `200 OK`
```json
{ "cantidad": 3, "notas": "sin cebolla, bien cocida" }
```
Si no se envía `notas`, se conservan las actuales. **Quitar**: `DELETE` a la misma ruta, sin cuerpo.

**HU-04 — Entregar** · `PUT /api/v1/pedidos/1/entregar` (sin cuerpo) · `200 OK`
**HU-05 — Cancelar** · `DELETE /api/v1/pedidos/1` (sin cuerpo) · `200 OK`

## ⚠️ Errores

Formato: `{ "error": "mensaje", "codigo": "CODIGO" }`

| HTTP | Códigos |
|---|---|
| 400 | `JSON_INVALIDO`, `CAMPO_REQUERIDO`, `CAMPO_INVALIDO`, `CANTIDAD_INVALIDA`, `ESTADO_INVALIDO` |
| 401 | `NO_AUTENTICADO` (falta `X-Usuario-Id`) |
| 403 | `ACCESO_DENEGADO` (rol incorrecto o pedido de otro mesero) |
| 404 | `PEDIDO_NO_EXISTE`, `MESA_NO_EXISTE`, `PRODUCTO_NO_EXISTE`, `DETALLE_NO_EXISTE` |
| 409 | `MESA_OCUPADA`, `PEDIDO_BLOQUEADO` (editar fuera de PENDIENTE), `PRODUCTO_NO_DISPONIBLE`, `TRANSICION_INVALIDA`, `CANCELACION_NO_PERMITIDA` |
| 503 | `BD_NO_DISPONIBLE` |

## ✅ Pruebas automáticas

Con MySQL levantado y el `.env` configurado:

```bash
pytest -v
```

Cubre las 5 HU con casos felices y de error (mesa ocupada, rol incorrecto, pedido ajeno, edición bloqueada,
entregar sin estar LISTO, cancelar un pedido ENTREGADO, etc.). Cada prueba deja las mesas libres al terminar.

## 📝 Nota sobre el backend

`sp_cambiar_estado` solo permite cancelar desde `PENDIENTE` o `EN_PREPARACION`. Un pedido en `LISTO` responde
`409 TRANSICION_INVALIDA` al cancelarlo, aunque HU-05 dice "siempre que no haya sido entregado".
Si el equipo decide permitirlo, basta agregar `OR (v_actual = 'LISTO' AND p_nuevo = 'CANCELADO')` a la
validación de ese procedimiento; la API no necesita cambios.
