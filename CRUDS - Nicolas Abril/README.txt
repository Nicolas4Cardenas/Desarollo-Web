# 🍽️ Polirestaurante — CRUD como servicio REST (FastAPI + Postman)

Servicio REST en **FastAPI** con las funcionalidades de **cocina, historial de estados y reportes**
(**HU-06, HU-07, HU-08, HU-13, HU-14 y HU-15**), probado desde **Postman**.

Se conecta al backend MySQL del proyecto (`backend.sql`) llamando a sus **procedimientos almacenados**, así que las
reglas de negocio (transiciones de estado, control de rol, transacciones e historial inmutable) siguen viviendo en la
base de datos. Esta API es una capa delgada que recibe la petición HTTP, llama al procedimiento y traduce el
resultado o el error a JSON y a un código HTTP.

| HU | Funcionalidad | Método y ruta |
|---|---|---|
| HU-06 | Ver cola de pedidos pendientes | `GET /cocina/pedidos?id_usuario=4` |
| HU-07 | Pasar un pedido a "En preparación" | `PUT /cocina/pedidos/{id_pedido}/en-preparacion` |
| HU-08 | Marcar un pedido como "Listo" | `PUT /cocina/pedidos/{id_pedido}/listo` |
| HU-13 | Reporte de ventas | `GET /reportes/ventas?id_usuario=1&desde=...&hasta=...` |
| HU-14 | Reporte de tiempos de preparación | `GET /reportes/tiempos?id_usuario=1&desde=...&hasta=...` |
| HU-15 | CRUD del historial de estados | `POST/GET /historial`, `GET /historial/{id}` (PUT y DELETE bloqueados) |

---

## 📁 Estructura

```text
CRUDS - Nicolas Abril/
├── app/
│   ├── main.py                 # punto de entrada: crea la app y registra los routers
│   ├── db.py                   # conexión a MySQL y llamada a procedimientos (llamar_sp)
│   └── routers/
│       ├── cocina.py           # HU-06, HU-07, HU-08
│       ├── reportes.py         # HU-13, HU-14
│       └── historial.py        # HU-15 (CRUD de historial_estado)
├── postman/                    # colección de Postman lista para importar
├── requirements.txt
├── .env.example                # plantilla de configuración (sin contraseña)
└── README.md
```

Flujo de una petición: **ruta (router) → `llamar_sp` → procedimiento almacenado (MySQL)**.
Los errores de la base (`ACCESO_DENEGADO`, `TRANSICION_INVALIDA`, etc.) se convierten en códigos HTTP en `db.py`.

---

# ▶️ Parte 1. Instrucciones: cómo ejecutarlo

**Requisitos:** Python 3.10 o superior, MySQL 8 (con MySQL Workbench) y Postman.

### Paso 1. Crear la base de datos

El esquema oficial del grupo está en `backend.sql`, dentro de `BackendPolirestaurante.rar`, en la raíz del repositorio.

1. Descomprimir `BackendPolirestaurante.rar`.
2. Abrir `backend.sql` en MySQL Workbench y ejecutarlo completo (`Ctrl + Shift + Enter`, sin texto seleccionado).
3. Comprobar que cargó:

```sql
SELECT id_usuario, usuario_login FROM poli_restaurante.usuario;
```

Deben salir 4 usuarios: `admin`, `mesero1`, `mesero2` y `cocina1`.

> ⚠️ El script empieza con `DROP DATABASE IF EXISTS poli_restaurante`: **borra y vuelve a crear la base**.

### Paso 2. Instalar las dependencias

Desde la carpeta `CRUDS - Nicolas Abril`:

```bash
python -m venv venv
```

Activar el entorno virtual:

- Windows (PowerShell): `venv\Scripts\activate`
- Git Bash / MSYS2: `source venv/Scripts/activate`
- Mac / Linux: `source venv/bin/activate`

Instalar:

```bash
pip install -r requirements.txt
```

### Paso 3. Configurar la conexión

Copiar la plantilla y poner la contraseña de MySQL:

```bash
copy .env.example .env        # Mac / Linux: cp .env.example .env
```

Editar `.env`:

```text
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_contraseña
DB_NAME=poli_restaurante
```

El archivo `.env` está en el `.gitignore`: no se sube al repositorio.

### Paso 4. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

Debe aparecer `Application startup complete.`. Para comprobar que todo conecta, abrir en el navegador:

- `http://127.0.0.1:8000/salud` → devuelve `"estado": "ok"` y las tablas de la base.
- `http://127.0.0.1:8000/docs` → documentación interactiva (Swagger) con todos los endpoints.

---

# 🧭 Parte 2. Guía de uso: qué hace cada endpoint

## 🔐 Identificación del usuario

Esta API **no hace login** (la autenticación con JWT es HU-16 y corresponde a otro integrante). En su lugar, cada
petición indica qué usuario actúa, y **la base de datos valida su rol**:

- En las peticiones `GET`, como parámetro de la URL: `?id_usuario=4`
- En las peticiones `PUT` y `POST`, en el cuerpo JSON: `{"id_usuario": 4}`

Usuarios de los datos semilla de `backend.sql`:

| id_usuario | Login | Rol |
|---|---|---|
| 1 | admin | ADMINISTRADOR |
| 2 | mesero1 | MESERO |
| 3 | mesero2 | MESERO |
| 4 | cocina1 | COCINA |

Estados de un pedido: `PENDIENTE → EN_PREPARACION → LISTO → ENTREGADO` (y `CANCELADO`).

---

## 🧑‍🍳 Cocina (HU-06, HU-07, HU-08) — rol COCINA

### HU-06 — Ver la cola de pedidos pendientes

`GET /cocina/pedidos?id_usuario=4` · `200 OK`

Devuelve solo los pedidos en estado `PENDIENTE` (con al menos un producto), ordenados por fecha de creación,
cada uno con su mesa y el detalle de sus productos.

```json
[
  {
    "id_pedido": 1,
    "fecha_creacion": "2026-10-11T17:11:11",
    "mesas": "1",
    "detalle": [
      { "producto": "Hamburguesa clásica", "cantidad": 2, "notas": "sin cebolla" },
      { "producto": "Gaseosa", "cantidad": 2, "notas": null }
    ]
  }
]
```

### HU-07 — Pasar a "En preparación"

`PUT /cocina/pedidos/1/en-preparacion` · `200 OK`

```json
{ "id_usuario": 4 }
```

```json
{ "id_pedido": 1, "estado": "EN_PREPARACION" }
```

Solo es válido desde `PENDIENTE`. El cambio queda registrado automáticamente en el historial (con fecha, hora y usuario).

### HU-08 — Marcar como "Listo"

`PUT /cocina/pedidos/1/listo` · `200 OK`

```json
{ "id_usuario": 4 }
```

```json
{ "id_pedido": 1, "estado": "LISTO" }
```

Solo es válido desde `EN_PREPARACION`.

---

## 📊 Reportes (HU-13, HU-14) — rol ADMINISTRADOR

### HU-13 — Reporte de ventas

`GET /reportes/ventas?id_usuario=1&desde=2026-10-01&hasta=2026-10-31` · `200 OK`

Parámetros opcionales: `id_categoria` y `id_producto`. Solo cuentan los pedidos en estado `ENTREGADO`.

```json
{
  "desde": "2026-10-01",
  "hasta": "2026-10-31",
  "totales": { "pedidos_entregados": 1, "productos_vendidos": 4, "total_ventas": 53000.0 },
  "por_categoria": [ ... ],
  "por_producto": [ ... ]
}
```

### HU-14 — Reporte de tiempos de preparación

`GET /reportes/tiempos?id_usuario=1&desde=2026-10-01&hasta=2026-10-31` · `200 OK`

Calcula los tiempos a partir de `historial_estado`: minutos en cola, de preparación, de espera para la entrega y
totales, por pedido y como promedio del periodo.

```json
{
  "desde": "2026-10-01",
  "hasta": "2026-10-31",
  "por_pedido": [
    { "id_pedido": 1, "min_espera_en_cola": 1.8333, "min_preparacion": 0.35,
      "min_espera_entrega": 1.1667, "min_total": 3.35 }
  ],
  "promedio_periodo": { "pedidos_preparados": 1, "prom_min_preparacion": 0.35, "prom_min_total": 3.35 }
}
```

Los pedidos que aún no han avanzado aparecen con los tiempos en `null`.

---

## 🗂️ Historial de estados (HU-15) — CRUD

| Operación | Método y ruta | Resultado |
|---|---|---|
| Crear | `POST /historial` | `201` con el registro creado |
| Listar | `GET /historial` (opcional `?id_pedido=1`) | `200` con la lista |
| Obtener | `GET /historial/{id_historial}` | `200` con el registro, o `404` |
| Actualizar | `PUT /historial/{id_historial}` | `403`: el historial es inmutable |
| Borrar | `DELETE /historial/{id_historial}` | `403`: el historial es inmutable |

Cuerpo del `POST`:

```json
{ "id_pedido": 1, "estado": "PENDIENTE", "id_usuario_cambio": 1 }
```

El historial es **inmutable** (RNF-11): la API rechaza editar y borrar, y además lo bloquean triggers en la base de datos.
Los cambios de estado de cocina crean su registro de historial de forma automática; este `POST` permite además crear
registros manualmente. Estados válidos: `PENDIENTE`, `EN_PREPARACION`, `LISTO`, `ENTREGADO`, `CANCELADO`.

> Nota: este router usa SQL directo sobre la tabla `historial_estado` (no hay procedimiento almacenado de CRUD para ella);
> los demás routers llaman procedimientos.

---

## ⚠️ Errores

Formato de la respuesta: `{ "detail": "CODIGO: mensaje" }`

| HTTP | Cuándo |
|---|---|
| 400 | Rango de fechas inválido (`RANGO_INVALIDO`), estado no válido en el historial |
| 403 | `ACCESO_DENEGADO` (el rol no corresponde), o intento de editar o borrar el historial |
| 404 | `PEDIDO_NO_EXISTE`, o registro o usuario inexistente |
| 409 | `TRANSICION_INVALIDA` (cambio de estado no permitido), `PEDIDO_VACIO` (sin productos) |
| 422 | Falta un campo obligatorio (validación automática de FastAPI) |

---

# 📮 Parte 3. Probar con Postman

1. Importar `postman/PoliRestaurante - Nicolas.postman_collection.json` (*Import* en Postman).
2. Con la API corriendo, ejecutar las peticiones **en orden**: cambian el estado de los pedidos.
3. Antes de empezar, la base necesita pedidos de prueba. Ejecutar en MySQL Workbench:

```sql
USE poli_restaurante;
CALL sp_mesero_crear_pedido(2, 1, @p1);
CALL sp_mesero_agregar_producto(2, @p1, 3, 2, 'sin cebolla');
CALL sp_mesero_agregar_producto(2, @p1, 5, 2, NULL);
CALL sp_mesero_crear_pedido(3, 2, @p2);
CALL sp_mesero_agregar_producto(3, @p2, 4, 1, 'sin salsa');
CALL sp_mesero_crear_pedido(3, 3, @p3);
CALL sp_mesero_agregar_producto(3, @p3, 1, 1, NULL);
```

4. Para los **reportes** hace falta un pedido entregado. Esa acción es del mesero (HU-04, otro integrante), así que se
   hace a mano en Workbench, después de pasar el pedido 1 por cocina (`en-preparacion` y `listo`):

```sql
CALL sp_mesero_marcar_entregado(2, 1);
```

Con esos datos, el reporte de ventas del mes devuelve `pedidos_entregados: 1`, `productos_vendidos: 4` y `total_ventas: 53000`.

Para repetir las pruebas desde cero: volver a ejecutar `backend.sql` y los `CALL` del punto 3.

| Carpeta de la colección | Qué prueba | Códigos esperados |
|---|---|---|
| Historial | Crear, listar, filtrar, obtener, PUT y DELETE bloqueados, errores | `201`, `200`, `403`, `404`, `400` |
| Cocina | Cola, rol incorrecto, cambios de estado válidos e inválidos | `200`, `403`, `409`, `404` |
| Reportes | Ventas, tiempos, sin permiso, rango inválido | `200`, `403`, `400` |

---

## 📝 Alcance

- Esta carpeta cubre las HU-06, 07, 08, 13, 14 y 15. El módulo del mesero (HU-01 a 05) está en `CRUDS - Juan Parra`,
  y la administración del menú, mesas y usuarios (HU-09 a 12) y la autenticación (HU-16), a cargo de otro integrante.
- No hay login ni JWT en esta API: el usuario se identifica con `id_usuario`.
- El esquema de la base de datos es el de `backend.sql`; esta carpeta no lo modifica.

## 🤝 Autor

Nicolas Abril Cárdenas — Desarrollo de Software, Politécnico Grancolombiano.
