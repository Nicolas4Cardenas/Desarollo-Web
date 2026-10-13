# Polirestaurante — CRUDs de Nicolas Abril (cocina, historial y reportes)

Servicio REST en **FastAPI** + **MySQL 8**, probado con **Postman**.
Cubre **HU-06, HU-07, HU-08** (cocina), **HU-13, HU-14** (reportes) y **HU-15** (historial de estados).

Las mismas funcionalidades están hechas de **tres formas**, para comparar cómo se accede a la base de datos:

| Modalidad | Prefijo de la ruta | Cómo accede a MySQL | Archivos (`app/routers/`) |
|---|---|---|---|
| **REST con procedimientos almacenados** | `/cocina/...` y `/reportes/...` | `CALL sp_*`: las reglas viven en la base | `cocina.py`, `reportes.py` |
| **Driver** (acceso directo a tablas) | `/driver/cocina/...`, `/driver/reportes/...` y `/historial` | SQL escrito a mano con `mysql-connector` | `cocina_driver.py`, `reportes_driver.py`, `historial.py` |
| **ORM** | `/orm/...` | Clases de SQLAlchemy (`models.py`), sin SQL a mano | `cocina_orm.py`, `reportes_orm.py`, `historial_orm.py` |

Las tres usan **la misma base de datos** y deben dar **los mismos resultados**.

---

#  1. Ponerlo a funcionar (sirve desde cualquier PC)

**Programas necesarios:** Python 3.10+, MySQL 8 con MySQL Workbench, Postman y VS Code.

### Paso 1 — Obtener el proyecto
```bash
git clone https://github.com/Nicolas4Cardenas/Desarollo-Web.git
cd "Desarollo-Web/CRUDS - Nicolas Abril"
```
(Sin Git: en GitHub, *Code → Download ZIP*, descomprimir y entrar a la carpeta `CRUDS - Nicolas Abril`.)

### Paso 2 — Crear la base de datos
1. En la raíz del repositorio, descomprimir `BackendPolirestaurante.rar` (contiene `backend.sql`).
2. Abrir **MySQL Workbench**, conectarse a la instancia local (*Local instance MySQL80*).
3. *File → Open SQL Script* → elegir `backend.sql`. Sin texto seleccionado, pulsar el rayo ⚡ (o `Ctrl + Shift + Enter`).
4. Comprobar que cargó. Debe devolver 4 usuarios (`admin`, `mesero1`, `mesero2`, `cocina1`):
```sql
SELECT id_usuario, usuario_login FROM poli_restaurante.usuario;
```
>  `backend.sql` borra y recrea la base `poli_restaurante`.

### Paso 3 — Cargar los datos de demostración
En Workbench: abrir `sql/datos_demo.sql` y ejecutarlo. Al final debe mostrar `1, 2, 3, 4`
(cuatro pedidos pendientes; cada modalidad usa el suyo).

### Paso 4 — Instalar Python y dependencias
Desde la carpeta `CRUDS - Nicolas Abril`:
```bash
python -m venv venv
venv\Scripts\activate            # Windows PowerShell
# source venv/Scripts/activate   # Git Bash
# source venv/bin/activate       # Mac / Linux
pip install -r requirements.txt
```
Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

### Paso 5 — Configurar la conexión
```bash
copy .env.example .env           # Mac / Linux: cp .env.example .env
```
Abrir `.env` y escribir la contraseña de MySQL en `DB_PASSWORD=`. (`.env` no se sube a Git.)

### Paso 6 — Levantar el servidor
```bash
uvicorn app.main:app --reload
```
Debe aparecer `Application startup complete.` Dejar esa terminal abierta. Comprobar en el navegador:
- `http://127.0.0.1:8000/salud` → `"estado": "ok"` y la lista de tablas.
- `http://127.0.0.1:8000/docs` → todos los endpoints, agrupados por modalidad (se pueden probar desde ahí).

### Paso 7 — Importar las pruebas en Postman
*Import* → `postman/PoliRestaurante - Nicolas.postman_collection.json`.
Cada petición trae su prueba automática (verde si responde el código esperado).

---

# 🎤 2. Guion de sustentación (unos 10–12 minutos)

**Preparación (antes de entrar):** pasos 1 a 6 hechos, base recién cargada con `backend.sql` + `datos_demo.sql`,
servidor corriendo, Postman con la colección importada y MySQL Workbench y VS Code abiertos.

### A. Presentar (1 min) — *tabla de arriba*
Decir qué HU se hicieron y que hay tres modalidades sobre la misma base. No hay login: el usuario se indica con
`id_usuario` y **la base valida el rol** (1 admin, 2–3 meseros, 4 cocina). El login con JWT es HU-16, de otro integrante.

### B. La base de datos (2 min) — *MySQL Workbench*
Abrir `backend.sql` y mostrar: las tablas (`pedido`, `detalle_pedido`, `historial_estado`…), un procedimiento
(`sp_cocina_iniciar_preparacion`) y los **triggers** que impiden editar o borrar el historial.
Idea clave: *las reglas de negocio ya existen en la base; el servicio REST las expone por HTTP.*

### C. El código, tres formas de hacer lo mismo (3 min) — *VS Code, carpeta `app/`*
1. `db.py` → `llamar_sp`: llama un procedimiento y traduce sus errores a códigos HTTP.
2. `routers/cocina.py` → una línea por endpoint: `llamar_sp("sp_cocina_iniciar_preparacion", ...)`.
3. `routers/cocina_driver.py` → **SQL escrito a mano** con `mysql-connector`. Las reglas (rol, transición válida,
   historial) pasan a Python, dentro de **una transacción**: `start_transaction`, `SELECT ... FOR UPDATE`, `commit` / `rollback`.
4. `routers/cocina_orm.py` + `models.py` + `orm_db.py` → **clases** (`Pedido`, `HistorialEstado`…), consultas con
   `select()` y `session.commit()`. No se usa `create_all()`: las tablas las crea `backend.sql`.

### D. Demostración en Postman (4 min) — *ejecutar carpeta por carpeta (clic derecho → Run folder)*
| Carpeta | Qué mostrar | Qué explicar |
|---|---|---|
| **1 · Procedimientos** (pedido 1) | Cola, pasar a preparación, repetir el cambio (`409`), rol incorrecto (`403`), pedido inexistente (`404`), marcar listo | La base impide saltar estados y valida el rol |
| **2 · Driver** (pedido 2) | La misma carpeta | Mismos resultados, pero con SQL a mano |
| **3 · ORM** (pedido 3) | La misma carpeta | Mismos resultados, con clases |
| **4 · Historial** | Listar, obtener, crear; `PUT` y `DELETE` dan `403` | El historial es inmutable (RNF-11): la API y los triggers lo bloquean |

Antes de la carpeta 5, en Workbench ejecutar `sql/entregar_demo.sql` (entrega los pedidos 1, 2 y 3: esa acción es del mesero, HU-04).

| Carpeta | Qué mostrar | Qué explicar |
|---|---|---|
| **5 · Reportes** | Ventas y tiempos en las tres modalidades; sin permiso (`403`); rango de fechas inválido (`400`) | Con los datos de demo, ventas da **3 pedidos entregados, 12 productos y 159000**, y las tres versiones coinciden |

En `/historial?id_pedido=1` se ve el recorrido del pedido: `PENDIENTE → EN_PREPARACION → LISTO → ENTREGADO`,
con la fecha y el usuario de cada cambio (HU-15).

### E. Cierre (1 min)
Resumir: 3 modalidades, mismas reglas, historial inmutable, transacciones. Mencionar el alcance (abajo).

### Preguntas probables
- **¿Por qué tres versiones?** Para comparar: procedimientos (la lógica en la base), driver (SQL manual) y ORM (objetos).
- **¿Para qué sirve `FOR UPDATE`?** Bloquea la fila del pedido para que dos usuarios no cambien su estado a la vez.
- **¿Qué pasa si falla algo a la mitad?** `rollback`: no se guarda el cambio de estado ni su historial (RNF-10).
- **¿Por qué `PUT` y `DELETE` del historial dan `403`?** Porque es un registro de auditoría inmutable (RNF-11).
- **¿Por qué el ORM no crea las tablas?** Para no pisar el esquema oficial de `backend.sql`.
- **¿Dónde está la seguridad?** Cada operación valida el rol del `id_usuario`; el login con JWT es HU-16 (otro integrante).

---

# 🛠️ 3. Si algo falla

| Síntoma | Causa y solución |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Ejecutar `uvicorn` desde la carpeta `CRUDS - Nicolas Abril` |
| `Access denied for user 'root'` | Contraseña incorrecta en `.env` |
| `Can't connect to MySQL server` | Servicio MySQL apagado (Windows: *Servicios → MySQL80 → Iniciar*) |
| `ECONNREFUSED` en Postman | El servidor no está corriendo: repetir el paso 6 |
| `409` en una petición que debería dar `200` | El pedido ya cambió de estado. Repetir desde cero: `backend.sql` + `sql/datos_demo.sql` |
| `405 Method Not Allowed` | Método equivocado: la cola es `GET`; los cambios de estado son `PUT` |
| El puerto 8000 está ocupado | `uvicorn app.main:app --reload --port 8001` y cambiar `base_url` en Postman |

**Repetir la demo desde cero:** ejecutar de nuevo `backend.sql` y luego `sql/datos_demo.sql`.

---

#  4. Referencia de rutas

| HU | Procedimientos | Driver | ORM |
|---|---|---|---|
| HU-06 cola (`GET`) | `/cocina/pedidos?id_usuario=4` | `/driver/cocina/pedidos?id_usuario=4` | `/orm/cocina/pedidos?id_usuario=4` |
| HU-07 (`PUT`) | `/cocina/pedidos/{id}/en-preparacion` | `/driver/cocina/pedidos/{id}/en-preparacion` | `/orm/cocina/pedidos/{id}/en-preparacion` |
| HU-08 (`PUT`) | `/cocina/pedidos/{id}/listo` | `/driver/cocina/pedidos/{id}/listo` | `/orm/cocina/pedidos/{id}/listo` |
| HU-13 ventas (`GET`) | `/reportes/ventas` | `/driver/reportes/ventas` | `/orm/reportes/ventas` |
| HU-14 tiempos (`GET`) | `/reportes/tiempos` | `/driver/reportes/tiempos` | `/orm/reportes/tiempos` |
| HU-15 historial | — | `/historial` | `/orm/historial` |

- Los `PUT` llevan el cuerpo `{"id_usuario": 4}`. Los reportes piden `id_usuario=1`, `desde=2026-10-01` y `hasta=2026-10-31` (opcionales: `id_categoria`, `id_producto`).
- Historial: `POST` (crear, `201`), `GET` (listar, con `?id_pedido=`), `GET /{id}`, `PUT` y `DELETE` (`403`).
- Errores: `400` rango o estado inválido · `403` rol sin permiso o historial inmutable · `404` no existe · `409` cambio de estado no permitido o pedido sin productos · `422` falta un campo.

##  Alcance
- Esta carpeta cubre HU-06, 07, 08, 13, 14 y 15. El módulo del mesero (HU-01 a 05) está en `CRUDS - Juan Parra`.
- No hay login ni JWT: el usuario se identifica con `id_usuario`.
- El esquema es el de `backend.sql`; esta carpeta no lo modifica.

## 🤝 Autor
Nicolas Abril Cárdenas — Desarrollo de Software, Politécnico Grancolombiano.
