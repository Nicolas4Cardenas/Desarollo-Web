# PoliRestaurante · Menú interactivo (ORM + driver)

Menú de consola para el backend `backend.sql`. Usa **SQLAlchemy (ORM)** y el
driver **PyMySQL**. Un menú distinto por rol: MESERO, COCINA y ADMINISTRADOR.

## Cómo ejecutarlo

Necesitas Python 3.9+ y un servidor **MySQL 8 / MariaDB 10.5+** encendido
(usuario `root`, clave `12345`, puerto 3306 — igual que tu `config.py`).
¿No tienes MySQL? `docker compose up -d` levanta uno con esos datos.

| Sistema | Comando |
|---|---|
| Windows | doble clic en `iniciar.bat` |
| Linux / macOS | `./iniciar.sh` |
| Manual | `pip install -r requirements.txt` y luego `python menu.py` |

La primera vez, el programa **crea la base `poli_restaurante` solo**
(ejecuta `backend.sql` con tablas, triggers, procedimientos y datos demo).

Si tu MySQL usa otro usuario o clave: copia `.env.example` a `.env` y edítalo.

## Usuarios de prueba (del propio backend.sql)

| Usuario | Clave | Rol |
|---|---|---|
| admin | Admin2026* | ADMINISTRADOR |
| mesero1 / mesero2 | Mesero2026* | MESERO |
| cocina1 | Cocina2026* | COCINA |

## Cómo está armado

- **ORM (lecturas):** `poli/models.py` mapea las 9 tablas; `poli/consultas.py` hace los listados.
- **Driver (escrituras y reportes):** `poli/procedimientos.py` llama a los `sp_*` con PyMySQL.
  Así se respetan las reglas que ya viven en la base (roles, dueño del pedido,
  máquina de estados, historial inmutable).
- Las contraseñas se comparan/crean con **bcrypt** en la aplicación; la base solo guarda el hash.
- Opción "Reinstalar base de datos" en el menú de inicio: borra todo y vuelve a cargar `backend.sql`.

## Pruebas (sin base de datos)

`pytest` — valida el lector del `.sql` y el parseo de precios/fechas.
