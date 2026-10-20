# MySQL y Workbench, paso a paso

## Si ya usabas nuestro backend driver

La API usa el mismo esquema versión 1 de `polirestaurante_driver` y los mismos hashes de
contraseña. No necesitas migraciones, `db upgrade`, importar `esquema_mysql` antiguo ni
crear otro administrador. Copia **tu** `config_mysql.json` junto a `iniciar_api.py`, instala
`requirements-mysql.txt` e inicia con `--motor mysql`. Puedes cerrar la consola anterior
para presentar solo por Postman. Los datos previos se conservan.

La base SQLite de la nueva carpeta es independiente de la SQLite de `backend_driver`.
Para reutilizar un archivo SQLite existente usa `--base` con su ruta completa; no copies
archivos mientras otro proceso esté escribiendo.

## Instalación nueva con MySQL

1. Inicia el servicio MySQL y abre en Workbench la conexión root/instalador.
2. Archivo > Open SQL Script > `sql/mysql_01_esquema.sql`.
3. Ejecuta **todo el archivo** con el rayo sin selección de texto. Revisa Action Output.
   Crea la base `polirestaurante_driver`, 12 tablas y una fila técnica en `sistema`.
4. Abre `sql/mysql_02_usuario.sql`. Sustituye todas las apariciones de
   `TU_CLAVE_PRIVADA_DRIVER` por una contraseña tuya y ejecuta todo. No publiques el script
   modificado con tu contraseña. La cuenta `poli_driver_app` conecta Python con MySQL;
   **no** es el administrador ni el mesero del restaurante.
5. Refresca SCHEMAS. No basta con abrir los scripts; deben ejecutarse sin errores.
6. Copia `config_mysql.ejemplo.json` como **`config_mysql.json`** al lado de `iniciar_api.py`.
   No lo llames `config_mysql.json.json`. Activa extensiones de archivo en el Explorador.
   Pon host, puerto (entero), usuario de conexión, contraseña y base correctos.

```json
{
  "host": "127.0.0.1",
  "port": 3306,
  "user": "poli_driver_app",
  "password": "TU_CONTRASENA_DE_MYSQL",
  "database": "polirestaurante_driver"
}
```

En JSON no hay comentarios ni coma después del último campo. Si la contraseña contiene
comillas dobles o barras invertidas debes escaparlas según JSON. También puedes omitirla
del archivo y definir `POLI_DB_PASSWORD` en tu entorno.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-mysql.txt
.venv\Scripts\python.exe iniciar_api.py --motor mysql --verificar
.venv\Scripts\python.exe iniciar_api.py --motor mysql --crear-admin
.venv\Scripts\python.exe iniciar_api.py --motor mysql
```

`--crear-admin` se usa solo si no hay usuarios. Si ya hay usuarios, el programa lo indica
y no los sobrescribe. El catálogo se carga después con Postman como administrador.

## Comprobar que Postman sí modifica MySQL

Tras crear un pedido, ejecuta en Workbench:

```sql
USE polirestaurante_driver;
SELECT id, nombre, login, rol, activo FROM usuario;
SELECT id, nombre FROM categoria;
SELECT id, nombre, categoria_id, precio_centavos, disponible, activo FROM producto;
SELECT id, numero, capacidad, activa FROM mesa;
SELECT id, responsable_id, mesa_id, tipo, estado, version FROM pedido ORDER BY id DESC;
SELECT * FROM detalle ORDER BY id DESC;
SELECT * FROM historial ORDER BY id DESC;
SELECT * FROM ocupacion;
```

No necesitas mantener Workbench abierto: es un cliente; lo que debe seguir activo es el
servicio MySQL. Refresca la consulta después de enviar desde Postman. Si ves motor `sqlite`
en la terminal, detén y arranca con `--motor mysql`.

Las cuentas de conexión tienen permisos limitados. Historial, auditoría y resultados de
operaciones permiten SELECT/INSERT; no UPDATE/DELETE. No se piden SUPER ni triggers MySQL.
Estos SQL no eliminan bases antiguas; no fuerces esquemas incompatibles ni borres tablas
para solucionar un error. Respalda MySQL con Workbench > Server > Data Export.
