"""Dos drivers, una interfaz pequeña: sqlite3 incluido en Python y MySQL opcional.
No hay ORM, procedimientos ni instalaciones de MySQL hechas por la aplicación.
"""

from contextlib import contextmanager
from pathlib import Path
import json
import os
import sqlite3
from .errores import ErrorBase

RAIZ = Path(__file__).resolve().parents[1]


class Cursor:
    def __init__(self, cursor, motor):
        self.cursor, self.motor = cursor, motor

    def execute(self, sql, parametros=()):
        self.cursor.execute(
            sql.replace("?", "%s") if self.motor == "mysql" else sql, parametros
        )
        return self

    def one(self):
        fila = self.cursor.fetchone()
        return dict(fila) if fila is not None else None

    def all(self):
        return [dict(f) for f in self.cursor.fetchall()]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount


class Base:
    def __init__(self, motor="sqlite", ruta=None, configuracion=None):
        if motor not in ("sqlite", "mysql"):
            raise ErrorBase("Motor válido: sqlite o mysql.")
        self.motor = motor
        self.ruta = (
            Path(ruta).expanduser().resolve()
            if ruta
            else RAIZ / "datos" / "polirestaurante.db"
        )
        self.configuracion = configuracion or {}

    @classmethod
    def mysql_desde_archivo(cls, ruta):
        try:
            d = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
            if not isinstance(d, dict):
                raise ValueError
            for campo in ("host", "port", "user", "database"):
                if campo not in d:
                    raise ValueError
            if os.environ.get("POLI_DB_PASSWORD") is not None:
                d["password"] = os.environ["POLI_DB_PASSWORD"]
            if not all(
                isinstance(d[k], str) and d[k].strip()
                for k in ("host", "user", "database")
            ):
                raise ValueError
            if type(d["port"]) is not int or not 1 <= d["port"] <= 65535:
                raise ValueError
            if not isinstance(d.get("password", ""), str):
                raise ValueError
            return cls("mysql", configuracion=d)
        except (OSError, ValueError, TypeError):
            raise ErrorBase(
                "Revisa config_mysql.json: JSON válido con host, port, user, password y database."
            ) from None

    def _conectar(self):
        if self.motor == "sqlite":
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(self.ruta), timeout=15, isolation_level=None)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA busy_timeout=15000")
            return con
        try:
            import mysql.connector
        except ImportError:
            raise ErrorBase(
                "Modo MySQL: instala requirements-mysql.txt. SQLite funciona sin instalar paquetes."
            ) from None
        permitidos = {"host", "port", "user", "password", "database"}
        config = {k: v for k, v in self.configuracion.items() if k in permitidos}
        return mysql.connector.connect(
            **config,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            use_pure=True,
            autocommit=False,
            connection_timeout=10
        )

    def error(self, exc):
        codigo = getattr(exc, "errno", None)
        if isinstance(exc, sqlite3.IntegrityError) or codigo in (
            1062,
            1451,
            1452,
            3819,
            1048,
        ):
            return ErrorBase(
                "No se guardó: hay un valor duplicado o una relación/restricción protegida.",
                "CONFLICTO",
            )
        if codigo == 1045:
            return ErrorBase(
                "MySQL rechazó usuario o contraseña. Verifica config_mysql.json y la cuenta de conexión (no es el login del restaurante)."
            )
        if codigo == 1049:
            return ErrorBase(
                "La base MySQL no existe. Sigue docs/MYSQL.md; no importes SQL de versiones anteriores."
            )
        if codigo == 1146:
            return ErrorBase(
                "Faltan tablas MySQL. Ejecuta sql/mysql_01_esquema.sql como indica docs/MYSQL.md."
            )
        if isinstance(exc, sqlite3.DatabaseError):
            return ErrorBase(
                "No se completó la operación de SQLite. Revisa permiso de escritura, espacio y otras sesiones; no borres la base."
            )
        return ErrorBase(
            "No se confirmó la operación. Revisa servidor, configuración y permisos. Ante una respuesta incierta conserva la clave de operación."
        )

    @contextmanager
    def transaccion(self, escritura=False, instalando=False):
        con = None
        try:
            con = self._conectar()
            if self.motor == "sqlite":
                con.execute("BEGIN IMMEDIATE" if escritura else "BEGIN")
                cur = Cursor(con.cursor(), self.motor)
            else:
                con.start_transaction(isolation_level="READ COMMITTED")
                cur = Cursor(con.cursor(dictionary=True, buffered=True), self.motor)
                if escritura and not instalando:
                    # Conservador para una sustentación: las escrituras se serializan.
                    # El bloqueo se libera en commit/rollback, incluso con varios procesos.
                    cur.execute("SELECT id FROM sistema WHERE id=1 FOR UPDATE")
                    if cur.one() is None:
                        raise ErrorBase(
                            "Base no inicializada: falta la fila técnica sistema."
                        )
            yield cur
            con.commit()
        except Exception as exc:
            if con is not None:
                con.rollback()
            if isinstance(exc, sqlite3.Error) or exc.__class__.__module__.startswith(
                "mysql.connector"
            ):
                raise self.error(exc) from None
            raise
        finally:
            if con is not None:
                con.close()

    def inicializar(self):
        if self.motor == "mysql":
            self.verificar_esquema()
            return
        try:
            con = self._conectar()
            tablas = {
                f[0]
                for f in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if tablas and "sistema" not in tablas:
                raise ErrorBase(
                    "El archivo contiene otro esquema. Usa una ruta nueva; no se modificó el archivo."
                )
            if "sistema" in tablas:
                fila = con.execute("SELECT version FROM sistema WHERE id=1").fetchone()
                if not fila or fila[0] != 1:
                    raise ErrorBase(
                        "Versión de base incompatible. No se modificaron sus tablas."
                    )
            sql = (RAIZ / "sql" / "esquema_sqlite.sql").read_text(encoding="utf-8")
            con.executescript("BEGIN IMMEDIATE;\n" + sql + "\nCOMMIT;")
        except sqlite3.Error as exc:
            if con is not None:
                con.rollback()
            raise self.error(exc) from None
        finally:
            if "con" in locals():
                con.close()
        self.verificar_esquema()

    def verificar_esquema(self):
        with self.transaccion() as cur:
            cur.execute("SELECT version FROM sistema WHERE id=1")
            fila = cur.one()
            if not fila or fila["version"] != 1:
                raise ErrorBase("La base no corresponde al backend driver versión 1.")
            esperadas = {
                "sistema",
                "usuario",
                "sesion",
                "categoria",
                "producto",
                "mesa",
                "pedido",
                "ocupacion",
                "detalle",
                "historial",
                "auditoria",
                "operacion",
            }
            if self.motor == "sqlite":
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tablas = {x["name"] for x in cur.all()}
            else:
                cur.execute(
                    "SELECT TABLE_NAME AS nombre FROM information_schema.tables WHERE table_schema=DATABASE()"
                )
                tablas = {x["nombre"] for x in cur.all()}
            if not esperadas.issubset(tablas):
                raise ErrorBase(
                    "Esquema incompleto. Conserva los datos y revisa la guía de instalación."
                )

    def respaldo_sqlite(self, destino):
        if self.motor != "sqlite":
            raise ErrorBase("Para respaldar MySQL usa Workbench: Server > Data Export.")
        destino = Path(destino).expanduser().resolve()
        if destino == self.ruta or destino.exists():
            raise ErrorBase(
                "El respaldo debe ser un archivo nuevo, distinto de la base activa."
            )
        destino.parent.mkdir(parents=True, exist_ok=True)
        origen = copia = None
        try:
            origen = self._conectar()
            copia = sqlite3.connect(str(destino))
            origen.backup(copia)
        except (sqlite3.Error, OSError):
            raise ErrorBase(
                "No se pudo guardar el respaldo en la ruta elegida."
            ) from None
        finally:
            if copia is not None:
                copia.close()
            if origen is not None:
                origen.close()
        return str(destino)
