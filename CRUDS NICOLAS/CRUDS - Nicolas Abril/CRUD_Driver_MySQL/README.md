# 🍽️ Polirestaurante — CRUD con driver de Nicolas (mysql-connector-python)

Aplicación de **consola** para **cocina, reportes e historial** (**HU-06, 07, 08, 13, 14 y 15**) que habla con MySQL
directamente con el **driver oficial `mysql-connector-python`**: el SQL se escribe a mano (`INSERT`, `SELECT`, `UPDATE`, `DELETE`)
y las reglas de negocio se aplican en Python. No usa ORM ni procedimientos almacenados.

## 📁 Estructura

```text
CRUD_Driver_MySQL/
├── main.py            # inicio de sesión y arranque
├── menu.py            # interfaz de consola (solo pide datos y muestra resultados)
├── servicio.py        # TODO el SQL y las reglas de negocio
├── validaciones.py    # validación de entrada (cantidad, estado, fechas, rangos)
├── errores.py         # ErrorNegocio (codigo + mensaje) y SIN_CAMBIO
├── config.py          # configuración desde .env
├── tests/test_crud.py # 28 pruebas automáticas (pytest)
├── requirements.txt
└── .env.example
```

## 🗄️ Base de datos

Usa la base local `poli_restaurante_nicolas`, creada con `../sql/backend_nicolas.sql` (copia del backend del grupo con los triggers
del historial quitados y procedimientos extra). Ejecuta ese script completo en MySQL Workbench antes de empezar; volver a ejecutarlo
deja la base limpia.

## ▶️ Cómo ejecutarlo

```bash
pip install -r requirements.txt
copy .env.example .env     # Windows (Linux/Mac: cp); edita usuario y contraseña de MySQL
python main.py
```

Al iniciar pide el usuario (sin contraseña, igual que el CRUD de Juan). Usuarios de prueba: `admin`, `mesero1`, `mesero2`, `cocina1`.
**El administrador puede ejecutar cualquier opción del menú** (cocina y mesero, también sobre pedidos de otros meseros); mesero y cocina solo las suyas. **Mis HU usan dos roles**, por eso el menú indica el rol de cada opción y la opción **20** permite cambiar de usuario sin cerrar el programa.

## 📋 Menú

| Opción | HU | Rol | Operación |
|---|---|---|---|
| 9 | HU-06 | COCINA | Ver cola de pedidos pendientes (con productos y mesa) |
| 10 | HU-07 | COCINA | Ver pedidos en preparación |
| 11 | HU-07 | COCINA | Iniciar preparación (PENDIENTE → EN_PREPARACION) |
| 12 | HU-08 | COCINA | Marcar listo (EN_PREPARACION → LISTO) |
| 13 | HU-13 | ADMIN | Reporte de ventas por rango, con filtro de categoría y producto |
| 14 | HU-14 | ADMIN | Reporte de tiempos (cola, preparación, entrega, total, promedios) |
| 15 | HU-15 | ADMIN | **Read:** listar historial (todo o por pedido) |
| 16 | HU-15 | ADMIN | **Read:** ver un registro |
| 17 | HU-15 | ADMIN | **Create:** crear registro de historial |
| 18 | HU-15 | ADMIN | **Update:** editar estado, fecha o usuario (lo que no se escribe se conserva) |
| 19 | HU-15 | ADMIN | **Delete:** eliminar registro (pide confirmación) |
| 1–8 | apoyo | MESERO / ADMIN | Menú, mesas, crear pedido, agregar producto, entregar, cancelar, listar y ver pedidos |

Las opciones 1 a 8 son HU de otros compañeros que mi parte necesita para funcionar de punta a punta: para tener algo que cocinar hay que
crear un pedido, y los reportes solo cuentan pedidos **ENTREGADOS**.

### Flujo de demostración

1. `mesero1` → opción 3 (crear pedido), opción 4 (agregar productos).
2. `cocina1` → 9 (ver cola), 11 (preparar), 10 (ver en preparación), 12 (listo).
3. `mesero1` → 5 (entregar).
4. `admin` → 13 (ventas), 14 (tiempos), 15 (historial del pedido) y el CRUD completo: 17 crear, 18 editar, 19 eliminar.

## 🧠 Cómo funciona

| Concepto | Dónde |
|---|---|
| Transacción por operación: `commit` si sale bien, `rollback` si falla | `transaccion()` en `servicio.py` |
| Bloqueo de la fila al cambiar de estado (`SELECT ... FOR UPDATE`) | `_pedido_bloqueado()` |
| Motor de estados con transiciones válidas | `TRANSICIONES` y `_cambiar_estado()` |
| Cada cambio queda en `historial_estado` | `_cambiar_estado()` |
| Validación de rol contra las tablas `usuario` y `rol` | `_exigir_rol()` |
| Consultas parametrizadas (`%s`), sin concatenar texto | todo `servicio.py` |
| Mesa vuelve a `libre` al entregar o cancelar | `_liberar_mesas()` |

**Reglas:** la cola solo muestra pedidos PENDIENTES con productos; no se puede preparar un pedido vacío (`PEDIDO_VACIO`); los estados solo avanzan
en orden (`TRANSICION_INVALIDA`); los reportes toman la fecha del estado ENTREGADO del historial y validan que `hasta` no sea anterior a `desde`.

**Errores** (`ErrorNegocio`): `ACCESO_DENEGADO`, `PEDIDO_NO_EXISTE`, `PEDIDO_VACIO`, `TRANSICION_INVALIDA`, `RANGO_INVALIDO`, `FECHA_INVALIDA`,
`ESTADO_INVALIDO`, `HISTORIAL_NO_EXISTE`, `USUARIO_NO_EXISTE`, `CAMPO_REQUERIDO`, `MESA_OCUPADA`, `PRODUCTO_NO_DISPONIBLE`...

## ✅ Pruebas

```bash
python -m pytest -v
```

28 pruebas contra la base real (cola, preparar, listo, reportes con rangos válidos e inválidos, CRUD completo de historial, roles incorrectos).
Dejan pedidos ENTREGADOS o CANCELADOS; para limpiar, ejecuta de nuevo `backend_nicolas.sql`.

## 🔄 Comparación con las otras versiones

| | REST (Flask) | **Driver** | ORM (SQLAlchemy) |
|---|---|---|---|
| Interfaz | Postman | consola | consola |
| Acceso a datos | procedimientos almacenados | **SQL a mano** | objetos y sesiones |
| Reglas de negocio | en la base de datos | **en Python** | en Python |
