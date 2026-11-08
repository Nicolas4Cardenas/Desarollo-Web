# PoliRestaurante · Guía de la presentación completa

Esta entrega conecta los módulos de la colección de Postman con la interfaz web. Usa el mismo backend Flask, el mismo esquema MySQL y el diseño de pedidos de Juan Parra. Las operaciones de la página se guardan en la base a la que apunta Flask. Esta versión añade 13 DAO y reportes en hora de Colombia sin cambiar el esquema ni las cuentas.

## 1. Abrir con tu MySQL actual (Windows)

1. Descomprime todo el ZIP y abre la carpeta **PoliRestaurante_Presentacion_Completa** en VS Code. Mantén juntas `backend_api` y `cliente_juan`.
2. Copia tu `config_mysql.json` de la entrega anterior dentro de `backend_api`. Ese archivo contiene la conexión de Python a MySQL. La cuenta del restaurante es otra: sus credenciales demo están en `CREDENCIALES_DEMO.txt`. Si tu esquema `polirestaurante_driver` ya funciona, no vuelvas a importarlo.
3. Con el servicio MySQL activo, abre una terminal en la carpeta principal y ejecuta:

   ```powershell
   cd backend_api
   python -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements-mysql.txt
   .venv\Scripts\python.exe iniciar_api.py --motor mysql --verificar
   ```

   Si esa carpeta ya tiene un entorno `.venv` válido, puedes usarlo. Ejecuta de nuevo el comando de requisitos para instalar `tzdata`, que proporciona la zona de Colombia también en Windows. Si Windows reconoce Python como `py`, úsalo para crear el entorno: `py -m venv .venv`.

4. Si **todavía no cargaste la demostración en esa base**, ejecuta lo siguiente. La carga agrega registros faltantes y conserva tus datos; volver a ejecutarla no duplica registros ni cambia las claves del demo.

   ```powershell
   .venv\Scripts\python.exe cargar_demo.py --motor mysql
   ```

   En una base nueva agrega **1 administrador, 3 meseros, 3 cocineros, 6 categorías, 20 productos y 12 mesas**. Si ya habías cargado las cuentas, puedes omitir este paso. Tampoco necesitas pulsar **Cargar menú inicial** en Pedidos: ese botón es para la carga básica de la entrega anterior.

5. Arranca el servidor y deja la terminal abierta:

   ```powershell
   .venv\Scripts\python.exe iniciar_api.py --motor mysql
   ```

6. Abre **http://127.0.0.1:5000/**. Inicia sesión con `admin.demo`, `juan.demo` o `cocina1.demo` y su contraseña del bloc de notas `CREDENCIALES_DEMO.txt`. La página maneja la sesión automáticamente. Puedes cerrar Workbench y Postman.

**MySQL desde cero.** Sigue los pasos de instalación de `backend_api/docs/MYSQL.md` para ejecutar `mysql_01_esquema.sql` y preparar la conexión con `mysql_02_usuario.sql`. Después vuelve al paso 3 y ejecuta la carga demo; esta ya crea a `admin.demo`. `--crear-admin` es una alternativa para una base vacía si quieres un dueño propio y no vas a cargar el demo. No uses `flask db upgrade` con esta versión del driver.

**Sin MySQL en el equipo de la universidad.** SQLite usa la misma interfaz y guarda sus propios datos en `backend_api/datos/polirestaurante.db`. Desde la carpeta principal:

```powershell
cd backend_api
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe cargar_demo.py
.venv\Scripts\python.exe iniciar_api.py
```

Abre la misma dirección. Los cambios en SQLite no se reflejan en Workbench. En Linux o macOS, crea el entorno con `python3 -m venv .venv` y sustituye `.venv\Scripts\python.exe` por `./.venv/bin/python`.

**Live Server para editar.** Con Flask activo, abre `cliente_juan/cliente.html` con **Open with Live Server**, en el puerto **5500**. Flask ya permite el origen local de Live Server. Para presentar basta abrir la dirección de Flask; Bootstrap viene incluido y no necesita conexión a un CDN.

## 2. Qué puede hacer cada rol

| Módulo | Administrador | Mesero | Cocina |
| --- | --- | --- | --- |
| Pedidos y detalle | Consulta todos. Crea a su nombre o para otro mesero/admin. Agrega, edita o quita líneas de pedidos pendientes. Avanza, entrega, cancela y reasigna según el estado. | Ve sus pedidos e historial. Crea en salón o para llevar. Agrega, edita y quita líneas mientras estén pendientes. Cancela pendientes o en preparación con motivo. Entrega los listos. | Consulta pedidos y su historial. No puede crear pedidos, cambiar líneas ni entregar. |
| Cola de cocina | Ve los abiertos por orden de llegada. Puede iniciar la preparación, marcar listo o reasignar un pedido en preparación. | No aparece. Ve el estado en sus pedidos. | Ve la cola de abiertos. Toma un pedido pendiente con productos; solo su cocinero asignado puede marcarlo listo, salvo el administrador. |
| Productos | Lista, consulta, crea, edita, cambia disponibilidad, archiva y reactiva. | Consulta los disponibles. | Consulta los disponibles. |
| Categorías | Lista, consulta, crea, cambia nombre y elimina cuando no hay referencias. | Consulta. | Consulta. |
| Mesas | Lista, consulta, crea, edita, archiva y reactiva las libres. | Consulta mesas activas y reserva una libre al crear un pedido de salón. | Consulta mesas activas. |
| Usuarios | Lista, consulta, crea, edita nombre/login/rol, restablece claves, desactiva y reactiva según las reglas. | Cambia su propia clave en Mi perfil. | Cambia su propia clave en Mi perfil. |
| Reportes, auditoría y datos | Consulta ventas, tiempos, acciones e historial general. | Consulta el historial de sus pedidos desde el detalle. | Consulta el historial del pedido desde su detalle. |
| Mi perfil | Ve cuenta, rol, motor y sus recibos. Cambia su propia clave y cierra sesión. | Igual, con su propia cuenta. | Igual, con su propia cuenta. |

## 3. Crear, editar, recuperar o retirar una cuenta desde la página

Entra como **admin.demo** y abre **Usuarios**:

| Si el profesor pide… | Haz esto |
| --- | --- |
| Crear un mesero, cocinero o administrador | **Crear usuario** → nombre completo, usuario único, rol y contraseña temporal (10 a 128 caracteres; sin espacios en los extremos). Deja **Cuenta activa** marcada y guarda. Entrega la clave temporal al titular. |
| Verificar el primer inicio de sesión | Cierra la sesión de administrador y entra con la cuenta nueva. Aparece el cambio obligatorio de clave. Usa la temporal en **Contraseña actual**, escribe y confirma la nueva, y vuelve a entrar con ella. |
| Editar nombre, usuario o rol | En su fila pulsa **Editar** y guarda. Deja vacía la nueva clave temporal si quieres conservar la clave actual. Los cambios de cuenta revocan sus sesiones, así que deberá volver a entrar. |
| Desbloquear o recuperar acceso | Pulsa **Restablecer clave**. Asigna una temporal; se quita el bloqueo y se cierran las sesiones. Si la cuenta estaba desactivada, actívala también antes de que intente entrar. |
| Retirar acceso | **Desactivar** → confirma. Sus pedidos e historial quedan guardados. Si tiene pedidos abiertos a su cargo, ciérralos o reasígnalos antes. |
| Volver a habilitar una cuenta | Filtra por **Inactivos** → **Editar** → marca **Cuenta activa** y guarda. |
| Cambiar tu propia contraseña | **Mi perfil → Cambiar mi contraseña**. Usa tu contraseña actual. La sesión se cierra tras guardar. |

El administrador puede editar su nombre o usuario, y vuelve a iniciar sesión con el usuario actualizado. No puede desactivar su propia cuenta ni cambiar su propio rol. El backend protege la disponibilidad de un administrador activo. Las contraseñas actuales no se muestran.

**Si se bloquea `admin.demo` y no tienes otro administrador:** con el motor de tu base, ejecuta desde `backend_api` el siguiente comando (quita `--motor mysql` si usas SQLite):

```powershell
.venv\Scripts\python.exe cargar_demo.py --motor mysql --restablecer-claves-demo
```

Esto restablece **las siete cuentas de la carga demo**, elimina sus bloqueos y cierra sus sesiones. Úsalo cuando quieras volver a las claves del bloc de notas. Si cambiaste el login o rol de una cuenta demo, o la desactivaste, el comando no sobrescribe ese cambio: un administrador activo debe revisar la cuenta.

## 4. Actualizar, eliminar y verificar cambios

| Apartado | Qué significa actualizar o eliminar |
| --- | --- |
| Categorías | **Editar** cambia el nombre. **Eliminar** borra una categoría sin productos asociados, incluidos archivados, y sin referencias en detalles históricos. Para ensayar, crea una categoría vacía y elimínala. |
| Productos | **Editar** cambia nombre, descripción, precio, categoría y disponibilidad. **Archivar** lo retira de pedidos nuevos; los pedidos anteriores conservan el precio y los datos registrados. Para reactivarlo, edita y marca **Producto activo** y **Disponible para pedidos**. |
| Mesas | **Editar** cambia número, capacidad y actividad si está libre. **Archivar** la retira de las mesas reservables. Reactiva con **Editar → Mesa activa**. Para modificar una mesa ocupada, primero entrega o cancela su pedido según los permisos. |
| Pedidos | Cambia estado y, como administrador, asignaciones. **Cancelar pedido** pide motivo y libera la mesa; conserva el historial. Los estados finales quedan como registro. |
| Líneas del pedido | Abre un pedido pendiente para agregar productos, editar cantidad u observaciones y **Quitar** una línea. Al iniciar preparación quedan fijas. |
| Reportes, historial y auditoría | Son consultas. Los cambios del negocio se hacen desde el módulo correspondiente. |

Los reportes se consultan por fechas de **Colombia (America/Bogota)**, ambas inclusive, con un máximo de 366 días. El filtro abarca el día completo en Colombia y las horas de inicio y listo se muestran en esa misma zona. Por ejemplo, una venta del 7 a las 8 p. m. sigue apareciendo el 7, aunque la marca UTC ya sea del 8. **Ventas** incluye pedidos entregados y admite filtros por categoría y producto. **Tiempos** mide entre el inicio de preparación y el estado listo. En **Datos e historial** puedes inspeccionar tablas autorizadas sin exponer claves ni sesiones. **Mi perfil → Buscar recibo** consulta el UUID de una operación de pedido de esa cuenta; en la misma pestaña aparece prellenado el último recibo confirmado.

## 5. Guion para sustentar en clase

1. **Administrador:** abre **Usuarios** y muestra los siete accesos de prueba. Crea un mesero temporal si lo piden. En **Categorías** crea y renombra una categoría vacía; puedes eliminarla al terminar. En **Productos** o **Mesas**, muestra un alta, una edición y el archivo con su reactivación.
2. **Juan:** entra como `juan.demo`. Crea un pedido **En el salón** sobre una mesa libre y agrega un producto. Edita la cantidad y muestra que el subtotal se recalcula. Agrega otra línea y quítala antes de enviar a cocina. En **Mesas** comprueba que quedó ocupada.
3. **Cocina:** cierra sesión y entra como `cocina1.demo`. Abre la orden desde **Cola de cocina**, pulsa **Iniciar preparación** y luego **Marcar listo**. El detalle muestra el historial.
4. **Juan:** vuelve a entrar, abre el pedido y pulsa **Marcar entregado**. En **Mesas** comprueba que está libre. Prueba aparte un pedido **Para llevar** o la cancelación con motivo.
5. **Administrador:** consulta la venta y el tiempo en **Reportes**, y comprueba las acciones en **Auditoría** y **Datos e historial**. Si quieres mostrar un relevo, abre otro pedido no finalizado y usa **Reasignar**; puedes cambiar de cocinero mientras está en preparación.

## 6. Explicación del código y solución de problemas

- **Presentación:** `cliente_juan/cliente.html` y sus estilos definen la interfaz. `js/views/` renderiza el HTML y `js/controllers/` coordina eventos. `js/models/` valida formularios y llama a la API con `fetch`. Ocultar acciones en la vista ayuda a orientar a cada rol; Flask valida realmente los permisos.
- **Backend:** `backend_api/poli/api.py` recibe las peticiones. `servicio.py` aplica reglas de negocio y coordina la base. El SQL de negocio está en `backend_api/poli/dao/`: **12 DAO de tabla y 1 de reportes**. En **Agregar producto a un pedido**, `PedidoDAO` consulta el pedido, `ProductoDAO` consulta el producto y su precio, y `DetalleDAO` guarda la línea. Los tres comparten la misma transacción. Consulta [DAO_FINAL.md](backend_api/docs/DAO_FINAL.md) para ver cada clase, sus operaciones y cómo mostrarla en la sustentación.
- **La página no conecta:** revisa la terminal de Flask y abre `http://127.0.0.1:5000/api/v1/salud`. Debe responder con `ok: true` y el motor esperado. Si cambiaste el puerto al arrancar, abre la dirección correspondiente. Si usas Live Server, revisa **Configuración de conexión** y que la API termine en `/api/v1`.
- **No veo mis datos:** mira el motor y la base que imprime Flask, o el motor en **Mi perfil**. Si dice SQLite cuando esperabas MySQL, detén el servidor y usa `--motor mysql` con tu configuración. Si abriste pedidos con otra cuenta de mesero, solo el responsable y los roles autorizados podrán verlos.
- **Hubo conflicto o se perdió la respuesta:** actualiza y revisa el estado. En pedidos, si aparece **Hay una operación por confirmar**, consulta su resultado o reintenta desde ese aviso. La página conserva la misma clave de operación para evitar que el reintento duplique el pedido o la línea. En mantenimiento de catálogos y usuarios, actualiza el listado antes de volver a enviar.
- **Postman sigue disponible** en `backend_api/postman/` para comparar las peticiones. Para presentar el flujo en el navegador no necesitas abrirlo.

Las claves demo son para práctica local. El paquete no contiene tu `config_mysql.json` ni copia tu base anterior.
