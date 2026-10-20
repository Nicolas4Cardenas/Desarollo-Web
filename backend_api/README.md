# PoliRestaurante · API REST con driver SQL

Entrega de backend para probar con **Postman, incluida su extensión oficial de VS Code**.
No contiene páginas web. Python ejecuta la API; Postman envía peticiones HTTP/JSON;
SQLite o MySQL guarda los cambios. No necesitas ejecutar el backend de consola ni el
frontend anterior. Flask es el servidor HTTP; el acceso a las tablas sigue siendo driver
SQL directo, sin ORM ni migraciones de Alembic.

## 1. Abre la carpeta correcta

Descomprime el ZIP y abre **backend_api** con Archivo > Abrir carpeta en VS Code.
La terminal debe mostrar esa carpeta y contener `iniciar_api.py`.
Se recomienda Python 3.11 o 3.12 (mínimo 3.10), VS Code y la extensión oficial **Postman**,
publicada por Postman. La extensión se instala desde Extensiones y requiere iniciar sesión
con la cuenta de Postman. Esa cuenta es distinta de los usuarios del restaurante.

## 2. Instala las dependencias (Windows, CMD o PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No necesitas activar el entorno: los comandos usan directamente su Python y evitan el
problema de políticas de PowerShell con `Activate.ps1`. Si el comando `python` no existe
pero tienes el lanzador, usa `py -3 -m venv .venv`.

En macOS/Linux: `python3 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`
y sustituye el prefijo de los siguientes comandos por `.venv/bin/python`.

## 3. Elige el motor antes de crear el administrador

### Opción A: SQLite para presentar sin instalar MySQL

```powershell
.venv\Scripts\python.exe iniciar_api.py --crear-admin
```

Escribe tu nombre, un login (por ejemplo `admin`) y **tu propia contraseña de mínimo 10
caracteres**, dos veces. No aparecen los caracteres al escribir: es normal.
Crea el dueño una sola vez. Después inicia:

```powershell
.venv\Scripts\python.exe iniciar_api.py
```

La base persistente se crea en `datos/polirestaurante.db`. Cerrar y abrir conserva los datos.
No se incluye una base precargada con credenciales. El catálogo se carga desde Postman en
el paso 4. Para otro archivo sin afectar el existente usa `--base datos/otra_presentacion.db`
en **ambos comandos**, primero crear administrador y después iniciar.

### Opción B: MySQL / Workbench

Si ya tienes funcionando **la base `polirestaurante_driver` del backend driver entregado
antes**, puedes usarla directamente: copia tu configuración a esta carpeta, instala las
nuevas dependencias e inicia con `--motor mysql`. **Tus usuarios, pedidos y contraseñas
siguen siendo los mismos**. No vuelvas a crear el dueño ni importes esquemas antiguos.
No mezcles esto con las bases del antiguo backend ORM o Flask de prueba.

Si aún no tienes esa base, sigue [docs/MYSQL.md](docs/MYSQL.md). Resumen:

1. Ejecuta `sql/mysql_01_esquema.sql` como root/instalador en Workbench.
2. Ajusta y ejecuta `sql/mysql_02_usuario.sql` para crear la cuenta de conexión.
3. Copia `config_mysql.ejemplo.json` a **`config_mysql.json`**, una sola extensión `.json`.
4. Instala y verifica:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-mysql.txt
.venv\Scripts\python.exe iniciar_api.py --motor mysql --verificar
```

Solo si la base no tiene usuarios todavía:

```powershell
.venv\Scripts\python.exe iniciar_api.py --motor mysql --crear-admin
```

Inicia el servidor:

```powershell
.venv\Scripts\python.exe iniciar_api.py --motor mysql
```

**Importante:** sin `--motor mysql` se usa SQLite, por lo que los cambios no aparecerán en
Workbench. El servidor imprime el motor y la base que realmente usa.

## 4. Importa Postman dentro de VS Code

1. Deja abierta la terminal del servidor. Dirección: `http://127.0.0.1:5000/api/v1`.
2. Abre el icono Postman e inicia sesión si lo solicita.
3. Usa **Import**, selecciona los archivos de la carpeta `postman`:
   - `PoliRestaurante.postman_collection.json` (75 peticiones organizadas por pasos).
   - `Local.postman_environment.json` (variables locales).
4. Selecciona el entorno **PoliRestaurante · Local**.
5. Edita `admin_login` y `admin_password` con los que creaste. Guarda los valores locales.
   El archivo entregado deja la contraseña del administrador vacía deliberadamente.
6. Ejecuta **00.1 Salud** y **00.2 Login administrador**, con el botón **Send**.
7. Ejecuta el resto de la carpeta **00**: carga el catálogo y obtiene sus IDs reales.
8. Sobre una base nueva sigue las carpetas **01, 02, 03, 04, 05, 06, 07 y 08** en orden.
   Los errores 401, 403, 409 y 422 que el nombre anuncia son pruebas esperadas, no fallos.

Las carpetas 01–02 crean y activan a Juan (MESERO) y Cocina. Incluyen contraseñas de
**ejemplo para clase**, visibles en el entorno, que puedes cambiar antes de enviarlas.
El administrador puede crear otros empleados desde POST `/usuarios`.

Si ya creaste empleados en la versión de consola, **no repitas sus altas**. En el entorno
pon sus logins y claves definitivas; ejecuta los dos «Login definitivo» de 02, y consulta
`GET /usuarios` con el administrador para asignar `mesero_id` y `cocina_id` correctos.
Después puedes recorrer 03–08. No compartas un entorno exportado con contraseñas/tokens reales.

[Guía detallada de Postman y solución de errores](docs/POSTMAN_VSCODE.md).

## 5. Qué incluye y cómo se relaciona

| Módulo | Operaciones | Quién |
|---|---|---|
| Autenticación | Login, perfil, cambio de contraseña, logout | Cada usuario |
| Usuarios | Crear, consultar, editar, restablecer clave y desactivar | Administrador |
| Categorías | Crear, consultar, editar, eliminar si no hay referencias | Administrador modifica; los roles consultan |
| Productos | Crear, consultar, editar precio/disponibilidad, archivar/reactivar | Administrador modifica; empleados ven disponibles |
| Mesas | Crear, consultar disponibilidad, editar, archivar/reactivar | Administrador modifica; empleados consultan |
| Pedidos HU01–HU05 | Crear, agregar, editar/quitar, entregar, cancelar | Mesero sobre sus pedidos; dueño sobre todos |
| Cocina | Cola FIFO, iniciar preparación, marcar listo | Cocina y administrador |
| Control | Reasignar, historial, auditoría, tablas reales y reportes | Administrador |

Carga explícita inicial: **4 categorías, 10 productos y 6 mesas**. No inserta empleados
ni pedidos automáticamente. Se confirma en una transacción y registra una marca en la
auditoría; repetirla no duplica ni restaura datos editados.

El pedido referencia al responsable y, para SALON, una mesa. El detalle enlaza producto y
categoría, y guarda copia histórica de nombres y precio. Cocina toma el pedido con su
propia cuenta. Entregar/cancelar libera la mesa sin borrar pedido ni historial.

El flujo permitido es `PENDIENTE → EN_PREPARACION → LISTO → ENTREGADO`. Solo PENDIENTE
permite editar líneas. Mesero cancela PENDIENTE o EN_PREPARACION; dueño también puede
cancelar LISTO con motivo. Nadie cambia un pedido ya cerrado ni salta pasos.

Los precios de entrada son texto decimal en pesos colombianos, por ejemplo
`"precio": "22000.00"`. Las respuestas usan centavos enteros:
`2200000` centavos son **COP 22.000**, no COP 2.200.000. Total = suma de cantidad × precio
histórico; el cliente no envía ni decide el total.

## 6. Documentación y explicación del código

- [Contrato completo de rutas y cuerpos JSON](docs/API.md).
- [Uso de Postman en VS Code y errores frecuentes](docs/POSTMAN_VSCODE.md).
- [MySQL, Workbench y reutilización de la base](docs/MYSQL.md).
- [Guion para explicar los archivos y depurar con VS Code](docs/EXPLICACION_CODIGO.md).
- [Cinco bloques por integrante y reglas del restaurante](docs/REPARTO_Y_REGLAS.md).
- [Validación y límites de esta entrega](docs/VALIDACION.md).
- [Cómo incorporar al repositorio](docs/SUBIR_AL_REPOSITORIO.md).

Las mutaciones de pedidos requieren `Idempotency-Key` (UUID) y la versión vigente del
pedido. La colección los administra. Si no llega respuesta, consulta la operación con la
misma cuenta y conserva su clave: no crees otra operación a ciegas.

## 7. Ejecutar pruebas

Desde `backend_api` con dependencias instaladas:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas usan archivos temporales y no modifican tu base. El servidor se escucha solo
en `127.0.0.1`, sin depurador web, para clase local. Para usar F5 abre **esta carpeta**,
selecciona `.venv` con Python: Select Interpreter, y elige «API · SQLite» o «API · MySQL».
Primero debes haber creado el administrador. No ejecutes F5 y el comando de terminal a la
vez sobre el mismo puerto.

No hace falta Node.js, Newman, Postman Desktop ni permisos de administrador para ejecutar
la API con SQLite; sí hace falta poder instalar sus paquetes Python y usar la extensión.
El servidor de Flask incluido es para desarrollo/presentación local. Inventario, pagos,
facturas fiscales y domicilios no forman parte de las HU implementadas.
