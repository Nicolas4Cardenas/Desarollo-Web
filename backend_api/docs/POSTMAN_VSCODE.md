# Postman dentro de VS Code

## Instalar e importar

Instala la extensión oficial [Postman](https://marketplace.visualstudio.com/items?itemName=Postman.postman-for-vscode),
abre su icono e inicia sesión con tu cuenta de Postman. Importa la colección y el entorno
JSON de `postman/` usando **Import** (archivo). Selecciona «PoliRestaurante · Local» y
configura `admin_login` y `admin_password`. El servidor Python debe seguir abierto.

La documentación oficial confirma peticiones, colecciones y entornos en la extensión:
[Descripción](https://learning.postman.com/latest-v-12/docs/reference/vs-code-extension/overview)
y [Importar archivos](https://learning.postman.com/latest-v-12/docs/reference/vs-code-extension/import-data/overview).
Los nombres exactos de paneles pueden variar con la versión instalada. Puedes enviar las
peticiones individualmente con Send; no dependes de disponer de un ejecutor de colecciones
en la interfaz. El mismo JSON también funciona en Postman Desktop.

## Primera presentación sobre una base nueva

| Carpeta | Qué hacer | Qué demuestra |
|---|---|---|
| 00 | Salud, login dueño, catálogo, listar categorías/productos/mesas | Conexión y datos relacionados |
| 01 | Crear Juan y cocinero | Solo el dueño registra empleados |
| 02 | Login temporal, cambio de clave y login definitivo | Roles y sesiones reales |
| 03 | Crear/consultar/editar/borrar recursos auxiliares | CRUD de administración |
| 04 | Enviar pruebas que esperan errores | Autorización en servidor |
| 05 | Pedido completo con edición/quitar y cocina | HU01–HU04 e historial |
| 06 | Nuevo pedido y cancelación con motivo | HU05 y liberación de mesa |
| 07 | Asignación por dueño, reportes y tablas | Control y persistencia |
| 08 | Cerrar sesiones | Revocación de tokens |

**No vuelvas a ejecutar 01–02 sobre los mismos empleados ya creados/activados.** Para una
segunda presentación vuelve a hacer login del dueño y los «Login definitivo» de ambos
roles; ejecuta listados de 00 y actualiza IDs de usuarios si cambiaste de base.
Para repetir 03 cambia `sufijo` y `mesa_prueba_numero`: los usuarios y mesas se archivan,
por lo que sus logins/números permanecen reservados. Un sufijo simple de letras/números
evita caracteres inválidos en `aux_<sufijo>`. Para repetir 05–06 selecciona una mesa libre
con 00.7; cada recorrido crea pedidos nuevos que quedan en el historial.

## Variables y automatización

- `base_url`: `http://127.0.0.1:5000/api/v1` (sin barra final).
- `admin_login/admin_password`: tus datos del dueño, contraseña vacía en el archivo entregado.
- `mesero_login`, `cocina_login`: empleados; contraseñas temporales/definitivas son ejemplos
  editables antes de crear las cuentas. No son contraseñas de MySQL ni de Postman.
- `token_admin`, `token_mesero`, `token_cocina`: se llenan en las respuestas de login.
  Cada petición tiene el Bearer del rol que realmente actúa. No cambies todo a token_admin.
- `mesa_id`, `producto_id`, `producto_extra_id`: IDs reales obtenidos de 00.
- `pedido_id`, `version`: guardados por las respuestas de cada mutación del pedido.
- `detalle_id`, `detalle_quitar_id`: capturados por GET 05.5, tras agregar ambas líneas.
- `desde/hasta`: fecha UTC de hoy si están vacías. Puedes poner `AAAA-MM-DD` (máximo 366 días).
- `ultima_clave`: UUID usada en la última mutación de pedido enviada.

En Scripts / Post-response (o Tests) hay comprobaciones de estado HTTP y respuesta.
Por ejemplo, 05.14 comprueba ENTREGADO, cuatro estados y COP 66.000 al precio inicial.
Si editaste el precio de la hamburguesa, ese importe esperado debe ajustarse a tu catálogo;
la API seguirá calculando con el precio guardado al agregar el producto.

Los scripts crean una UUID por operación de pedido y la guardan como `pendiente_<nombre>`
en el entorno. Al recibir una respuesta menor a 500, limpian esa clave pendiente. Ante un
error de transporte o 5xx la mantienen para reintentar **la misma petición, cuerpo y versión**.
No edites el cuerpo usando una clave pendiente anterior: recupera primero el resultado.
Consulta `GET /operaciones/{{ultima_clave}}` con el mismo usuario que hizo la solicitud.
Un 404 significa que no hay recibo confirmado para esa cuenta en el momento de consultar;
conserva la misma clave para reintentar. Para una operación nueva, elimina la variable
`pendiente_<nombre>` solo después de resolver la operación anterior.

## Petición manual de ejemplo

Para agregar un producto a un pedido pendiente:

- Método POST, URL `{{base_url}}/pedidos/{{pedido_id}}/detalles`.
- Authorization > Bearer Token > `{{token_mesero}}`.
- Header `Idempotency-Key`: una UUID minúscula, por ejemplo generada con la variable
  dinámica `{{$guid}}` (guarda el valor concreto si necesitas reintentar).
- Body > raw > JSON:

```json
{"producto_id":3,"cantidad":2,"notas":"Sin cebolla","version":1}
```

Los IDs y la versión del ejemplo se sustituyen por los que devuelva tu base. No envíes
`responsable_id` para fingir otro mesero ni totales calculados en el cliente.

## Errores frecuentes

| Síntoma | Causa / solución |
|---|---|
| ECONNREFUSED | API detenida, puerto distinto o URL incorrecta. Inicia Python y deja abierta su terminal |
| HTML/404 en `/` | La API vive en `/api/v1`; no hay página de inicio |
| Variables rojas o `{{pedido_id}}` literal | Selecciona el entorno e inicia el flujo anterior que llena ese ID |
| 401 | Falta token, expiró, se cerró sesión o cambiaste clave/usuario. Haz login de nuevo |
| 403 CAMBIAR_CLAVE | Cambia contraseña temporal y vuelve a iniciar sesión |
| 403 PERMISO | Rol incorrecto, pedido ajeno o cocinero distinto del asignado |
| 409 | Mesa ocupada, versión antigua, nombre duplicado o transición inválida. Lee `error.mensaje` |
| 415 | Selecciona Body > raw > JSON, Content-Type application/json |
| 422 | Falta campo, cantidad inválida o precio numérico. Envía precio como texto decimal |
| 429 | Cinco fallos de login. Espera 15 minutos o pide restablecimiento al dueño |
| 503 | Servidor/base/permisos MySQL. Revisa `--verificar` y docs/MYSQL.md |
| «JSON válido...» en terminal | Archivo debe llamarse exactamente config_mysql.json, una sola extensión |
| Port 5000 in use | Detén el servidor previo o usa `--puerto 5001` y cambia base_url |
| «Ya hay usuarios» | No repitas --crear-admin: usa el administrador que ya existe |
| Workbench no muestra los cambios | Comprueba motor mysql en terminal, base seleccionada y vuelve a ejecutar SELECT |
| ModuleNotFoundError flask/mysql | Instala requirements con el mismo `.venv\Scripts\python.exe` que usas al iniciar |
| 01 devuelve duplicado | Empleado ya existe; salta alta/cambio temporal y usa login definitivo |

No necesitas ejecutar `python -m flask ... db upgrade`. Esta API no usa Alembic.
Para comprobar sin Postman puedes visitar únicamente `/api/v1/salud` en el navegador;
las operaciones protegidas siguen necesitando Bearer.
