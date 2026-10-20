# MySQL opcional y Workbench

El modo SQLite funciona sin estos pasos. Elige MySQL solo si la clase lo exige o ya existe
un servidor disponible. No necesitas instalar MySQL dentro de cada PC si la universidad
permite conectarse a un servidor del curso.

## 1. Instalar el driver en el Python que vas a usar

Desde backend_driver:

```powershell
python -m pip install -r requirements-mysql.txt
```

Si no tienes permisos sobre el Python global, puedes usar `python -m venv .venv` y después
`.\.venv\Scripts\python.exe -m pip install -r requirements-mysql.txt`. Para ejecutar, usa ese
mismo `.\.venv\Scripts\python.exe`. No cambies políticas del equipo sin autorización.
Si no está disponible la instalación de paquetes ni un driver ya instalado, usa SQLite.

## 2. Preparar una base nueva desde Workbench

Conéctate como root o como instalador autorizado, en la misma instancia/puerto de MySQL
que usarás desde Python. No uses archivos de la entrega anterior.

1. Workbench → File → Open SQL Script → `sql/mysql_01_esquema.sql`.
2. Ejecuta todo el archivo con el rayo. Crea `polirestaurante_driver`, 12 tablas vacías y una
   fila técnica; no crea un administrador del restaurante ni ejemplos de productos/pedidos.
3. Abre `sql/mysql_02_usuario.sql`. Sustituye **todas** las apariciones de
   `TU_CLAVE_PRIVADA_DRIVER` por una contraseña privada para la conexión.
4. Ejecuta ese segundo archivo completo. Crea/actualiza `poli_driver_app` para localhost y
   127.0.0.1, con permisos por tabla. CREATE USER IF NOT EXISTS no cambia claves existentes;
   por eso el script también incluye ALTER USER.

La instalación usa tablas normales InnoDB: no hay funciones, procedimientos, triggers,
SUPER ni necesidad de desactivar controles del registro binario. El historial se protege
con permisos: la cuenta del programa solo puede SELECT/INSERT sobre historial, auditoría y
operaciones de reintento. Root conserva facultades de mantenimiento: no se debe usar como
cuenta diaria de la aplicación.

Los scripts son no destructivos: no incluyen DROP DATABASE ni DROP TABLE. IF NOT EXISTS
no convierte un esquema antiguo distinto al nuevo. La base driver debe ser nueva/versionada.

## 3. Configurar sin URL ni caracteres escapados

Copia `config_mysql.ejemplo.json` a `config_mysql.json`. Escribe la misma clave que pusiste
en el SQL. Al ser JSON no necesitas codificar `@` ni `:` como sucedía con DATABASE_URL.
Sí debes respetar las comillas y escapes propios de JSON si la clave contiene comillas o barras.

```json
{
  "host": "127.0.0.1",
  "port": 3306,
  "user": "poli_driver_app",
  "password": "TU_CLAVE_PRIVADA_DRIVER",
  "database": "polirestaurante_driver"
}
```

Ese archivo es privado y está ignorado por Git. Alternativamente define la contraseña con
la variable `POLI_DB_PASSWORD`; si existe, prevalece sobre el JSON. No la publiques en capturas.
Si vas a un servidor de la universidad, host, puerto y cuenta deben ser los que autorice
el administrador; no se crea acceso remoto general con `%` en los scripts.

## 4. Iniciar y crear al dueño

```powershell
python main.py --motor mysql --verificar
python main.py --motor mysql
```

En el primer inicio crea tu administrador dueño desde la consola. Esa cuenta puede crear
meseros, cocineros, otros administradores y todo el catálogo. No hay `flask db upgrade`,
`stamp`, `.env` ni creación de usuarios desde MySQL para cada mesero.

**Dos identidades diferentes:** `poli_driver_app` conecta Python con MySQL; el usuario que
creas en el menú (por ejemplo juan.admin) es una fila de la tabla usuario, con rol y hash.
El dueño de la aplicación no necesita root ni crear usuarios SQL para registrar empleados.

## 5. Ver que cambia la base de verdad

En Workbench abre una consulta nueva y ejecuta:

```sql
USE polirestaurante_driver;
SELECT id,nombre,login,rol,activo,debe_cambiar FROM usuario;
SELECT id,numero,capacidad,activa FROM mesa;
SELECT * FROM categoria;
SELECT id,nombre,precio_centavos,categoria_id,disponible,activo FROM producto;
SELECT * FROM pedido;
SELECT * FROM detalle;
SELECT * FROM ocupacion;
SELECT * FROM historial ORDER BY id;
SELECT * FROM auditoria ORDER BY id DESC;
```

Después de una operación en el menú, **vuelve a ejecutar** la consulta. La cuadrícula de
resultados de Workbench no se refresca sola. Los importes se guardan en centavos enteros:
18500 COP equivale a 1850000 centavos. Para ver pesos:

```sql
SELECT id,nombre,precio_centavos / 100.0 AS precio_cop FROM producto;
```

## Errores de conexión

- 1045: revisa host, usuario y clave del JSON; vuelve a ejecutar mysql_02_usuario.sql con
  la clave acordada en la misma instancia de MySQL, sin cambiar nombres de cuentas del menú.
- 1049: falta la base; ejecuta mysql_01_esquema.sql como instalador.
- 1146 o «faltan tablas»: comprueba que ejecutaste todo el esquema y la base del JSON coincide.
- Permiso denegado sobre historial/auditoría al editar manualmente: protección intencional.
  El backend solo inserta registros; no los borra ni modifica.
- Una cuenta que antes recibió permisos amplios debe revisarse con SHOW GRANTS. El script
  de concesión no revoca automáticamente permisos que alguien añadió por fuera.

Para copias MySQL usa Workbench → Server → Data Export, con una cuenta autorizada. No copies
archivos internos de MySQL como si fueran el archivo SQLite.
