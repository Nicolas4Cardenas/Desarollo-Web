# Contrato HTTP · /api/v1

Base local: `http://127.0.0.1:5000/api/v1`. JSON UTF-8, máximo 64 KiB por cuerpo.
No se admiten campos desconocidos en cuerpos de escritura. IDs/cantidades/versiones son
enteros JSON (no texto ni booleanos). Flags como `activo` son `true/false`.

Todas las rutas salvo salud y login requieren `Authorization: Bearer <token>`.
Las respuestas correctas tienen `{"ok":true,"datos":...}`; los errores:

```json
{"ok":false,"error":{"codigo":"PERMISO","mensaje":"Tu rol no permite esta operación."}}
```

## Autenticación

| Método | Ruta | Cuerpo / respuesta |
|---|---|---|
| GET | `/salud` | Motor y versión; también verifica acceso al esquema |
| POST | `/auth/login` | `{"login":"admin","password":"tu_clave"}` → token y usuario |
| GET | `/auth/me` | Perfil de la sesión (también funciona con clave temporal) |
| PUT | `/auth/password` | `{"actual":"clave_actual","nueva":"clave_nueva"}`; revoca todas las sesiones del usuario |
| POST | `/auth/logout` | Sin cuerpo; revoca el token actual |

Sesiones de ocho horas, contraseña de 10–128 caracteres, cinco fallos bloquean 15 minutos.
No hay registro público, JWT sin verificación ni permisos determinados por un rol recibido
en cada petición. El primer dueño se configura localmente con `--crear-admin` solo si la
base no tiene usuarios. Cuentas creadas o restablecidas por dueño requieren cambiar clave.

## Administración y catálogo

A = administrador; T = todos los roles con contraseña definitiva.

| Recurso | Listar / consultar | Crear | Actualizar completo | Eliminar |
|---|---|---|---|---|
| Usuarios (A) | GET `/usuarios`, `/usuarios/{id}` | POST `/usuarios` | PUT `/usuarios/{id}` | DELETE `/usuarios/{id}` desactiva |
| Categorías (consulta T; escritura A) | GET `/categorias`, `/categorias/{id}` | POST `/categorias` | PUT `/categorias/{id}` | DELETE `/categorias/{id}` si está vacía |
| Productos (consulta T; escritura A) | GET `/productos`, `/productos/{id}` | POST `/productos` | PUT `/productos/{id}` | DELETE `/productos/{id}` archiva |
| Mesas (consulta T; escritura A) | GET `/mesas`, `/mesas/{id}` | POST `/mesas` | PUT `/mesas/{id}` | DELETE `/mesas/{id}` archiva si está libre |

Cuerpos de creación y PUT (obligatorios los campos que aparecen; opcionales se indican abajo):

```json
{"nombre":"Juan Parra","login":"juan.parra","rol":"MESERO","password":"TemporalJuan123!"}
```

Usuario: `nombre`, `login`, `rol` obligatorios; `password` obligatorio al crear y opcional
al editar, `activo` opcional (por defecto true). Roles exactos: ADMINISTRADOR, MESERO,
COCINA. PUT con password restablece clave temporal y desbloquea; al editar revoca sesiones.
No puedes desactivarte, quitarte tu propio rol ni quitar al último administrador.
No se desactiva/cambia el rol de un empleado con pedidos abiertos asignados.

```json
{"nombre":"Bebidas"}
```

Categoría: solo `nombre`. Si contiene productos archivados o detalles históricos no se
elimina: 409. No hay borrado en cascada de ventas.

```json
{"nombre":"Limonada","descripcion":"Vaso natural","precio":"6000.00","categoria_id":3,"disponible":true,"activo":true}
```

Producto: nombre, descripcion (puede ser vacío), precio como **texto decimal** y categoria_id
obligatorios; disponible/activo opcionales (true). Cambiar el menú no modifica los detalles
anteriores. GET `/productos?incluir_archivados=true` permite al dueño ver todos; otros roles
siguen viendo solo activos/disponibles. PUT con activo/disponible true reactiva un producto.

```json
{"numero":7,"capacidad":4,"activa":true}
```

Mesa: numero/capacidad obligatorios; activa opcional (true). No se modifica si está ocupada.
GET `/mesas?incluir_archivadas=true` incluye archivadas solo para el dueño. La respuesta
incluye estado LIBRE/OCUPADA y pedido_id; no es un estado editable por el cliente.

**PUT es reemplazo de los campos editables**: envía el cuerpo completo y los flags que
quieres mantener; omitir un flag lo devuelve a su valor por defecto true. Para usuarios,
omitir password conserva el hash, pero la edición sí revoca sesiones. Para productos el
precio se envía en pesos con punto decimal y sin separador de miles, no precio_centavos.

POST `/admin/datos-iniciales` (A), cuerpo `{}`: carga catálogo de clase una sola vez.
En una base vacía inserta 4 categorías, 10 productos y 6 mesas. Si ya existen algunos nombres
o números los reutiliza sin sobrescribirlos. Repetir devuelve cargado false sin cambiar datos.

## Pedidos y detalles

Las mutaciones de esta sección exigen header **`Idempotency-Key`** con UUID minúscula.
Usa una nueva para cada operación nueva y conserva la misma con los mismos datos al
reintentar. El usuario autenticado forma parte de la clave. Todos los cambios de un pedido
existente exigen su versión vigente; una versión vieja devuelve 409.

| Método | Ruta | Rol / función |
|---|---|---|
| POST | `/pedidos` | Mesero/dueño crea pedido pendiente |
| GET | `/pedidos?estado=PENDIENTE&abiertos=true&pagina=1` | Mesero ve los propios; dueño/cocina tienen visibilidad global |
| GET | `/pedidos/{id}` | Pedido con detalles, total e historial; mesero solo propios |
| POST | `/pedidos/{id}/detalles` | Mesero responsable/dueño agrega producto |
| PUT | `/pedidos/{id}/detalles/{detalle_id}` | Mesero responsable/dueño edita cantidad/notas |
| DELETE | `/pedidos/{id}/detalles/{detalle_id}?version=3` | Mesero responsable/dueño quita la línea pendiente |
| PATCH | `/pedidos/{id}/estado` | Transiciones según rol y estado |
| PATCH | `/pedidos/{id}/asignacion` | Solo dueño reasigna responsable/cocinero |
| GET | `/cocina/cola?pagina=1` | Cocina/dueño consulta abiertos en orden de llegada |
| GET | `/operaciones/{uuid}` | Recibo confirmado, solo para el usuario que ejecutó la operación |

Crear salón: `{"tipo":"SALON","mesa_id":1}`. Para llevar: `{"tipo":"LLEVAR"}`.
El dueño puede añadir `responsable_id`; el mesero solo puede asignarse a sí mismo.
No se reserva una mesa ocupada/inactiva. Un pedido pendiente puede estar vacío, pero no
puede prepararse sin productos.

Agregar: `{"producto_id":3,"cantidad":2,"notas":"Sin cebolla","version":1}`.
`notas` es opcional al agregar, cantidad 1–99, máximo 100 líneas. El precio se obtiene de la
base, no del cliente. Repetir producto en líneas distintas es válido para notas distintas.

Editar: `{"cantidad":3,"notas":"Sin sal","version":2}`; todos obligatorios.
Quitar: versión en query, sin cuerpo DELETE. Solo se modifica un pedido PENDIENTE.
El detalle debe pertenecer al pedido de la URL.

Estado: `{"estado":"EN_PREPARACION","version":3}`; motivo opcional salvo cancelar.
Cancelar: `{"estado":"CANCELADO","version":3,"motivo":"Cliente se retira"}`.

| Estado previo | Estado solicitado | Quién |
|---|---|---|
| PENDIENTE con líneas | EN_PREPARACION | Cocina o dueño; registra cocinero que toma el pedido |
| EN_PREPARACION | LISTO | Cocinero asignado o dueño |
| LISTO | ENTREGADO | Mesero responsable o dueño |
| PENDIENTE / EN_PREPARACION | CANCELADO | Mesero responsable o dueño, con motivo |
| LISTO | CANCELADO | Solo dueño, con motivo de excepción |

No se vuelve atrás ni se cambia un pedido ENTREGADO/CANCELADO. Al cerrar se libera mesa,
se conserva el pedido y se inserta historial en la misma transacción. No hay DELETE del
pedido ni historial editable.

Reasignar: `{"responsable_id":2,"version":3,"motivo":"Cambio de turno"}` o
`{"cocinero_id":3,"version":3,"motivo":"Relevo"}`. Se exige al menos un ID válido;
responsable debe ser mesero/dueño activo; cocinero debe ser cocina/dueño activo y solo se
reasigna mientras EN_PREPARACION. La reasignación aumenta versión y deja auditoría.

Las mutaciones devuelven resumen `id, estado, version, total_centavos` y mensaje.
Consulta GET para recuperar detalles e historial. Un reintento idempotente devuelve el
resumen original de la operación; no el estado que pudo cambiar después.

## Reportes y auditoría (solo administrador)

| Método | Ruta | Consulta |
|---|---|---|
| GET | `/reportes/ventas?desde=2026-10-20&hasta=2026-10-20` | Solo entregados en el periodo, precio histórico, total y unidades |
| GET | `/reportes/ventas?...&categoria_id=2&producto_id=3` | Filtros opcionales enteros |
| GET | `/reportes/tiempos?desde=2026-10-20&hasta=2026-10-20` | De EN_PREPARACION a LISTO, excluye cancelados, promedio en segundos |
| GET | `/admin/auditoria?pagina=1` | Acciones realizadas y usuario |
| GET | `/admin/tablas/{tabla}?pagina=1` | Datos reales con lista permitida de tablas |

Fechas inclusivas, máximo 366 días, **UTC** como indica la respuesta. No se toma Bogotá
implícitamente para cortes diarios. Si no hay ventas devuelve total 0; sin preparaciones,
promedio null. Los listados de pedidos/cola/auditoría/tablas devuelven items, pagina y
hay_mas (50 filas por página). Catálogo y usuarios se listan completos para este alcance.

Tablas permitidas: usuario (sin hashes ni bloqueo), categoria, producto, mesa, pedido,
ocupacion, detalle, historial, auditoria y sistema. Sesiones y recibos no se exponen como
tablas generales. Esta ruta es solo lectura, no ejecuta SQL arbitrario.

## Estados HTTP

200 consulta/cambio correcto; 201 creación; 400 JSON malformado; 401 sesión/credenciales;
403 permiso/cambiar clave temporal; 404 inexistente; 405 método no permitido; 409 conflicto,
estado o versión; 413 cuerpo demasiado grande; 415 tipo de contenido; 422 datos inválidos;
429 cuenta bloqueada; 500 fallo inesperado; 503 base no disponible.

Ante 500/503 o pérdida de conexión, no asumas que la escritura falló: consulta su UUID con
la misma cuenta antes de repetir; conserva la clave. Los cambios de pedidos tienen recibo
atómico. Los CRUD de catálogo/usuarios no ofrecen idempotencia por UUID: tras pérdida de
respuesta consulta el recurso/listado antes de reenviar su creación.
