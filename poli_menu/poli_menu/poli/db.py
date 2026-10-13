"""Conexión: motor SQLAlchemy (ORM) + driver PyMySQL (procedimientos almacenados)."""
from pathlib import Path
from typing import Any, List

import pymysql
import pymysql.cursors
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from config import Config

from .sqlscript import dividir_sentencias

RUTA_SQL = Path(__file__).resolve().parent.parent / "backend.sql"
_engine = None  # type: Any


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = URL.create(
            "mysql+pymysql",
            username=Config.DB_USER,
            password=Config.DB_PASSWORD,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            query={"charset": "utf8mb4"},
        )
        _engine = create_engine(
            url, pool_pre_ping=True, connect_args={"autocommit": True}
        )
    return _engine


def _reiniciar_motor() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


# ---------------------------------------------------------------- instalación
def _conexion_servidor():
    """Conexión al servidor SIN seleccionar base (para poder crearla)."""
    return pymysql.connect(
        host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
        password=Config.DB_PASSWORD, charset="utf8mb4", autocommit=True,
    )


def base_instalada() -> bool:
    con = _conexion_servidor()
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT (SELECT COUNT(*) FROM information_schema.tables "
                "         WHERE table_schema=%s AND table_name='usuario'), "
                "       (SELECT COUNT(*) FROM information_schema.routines "
                "         WHERE table_schema=%s AND routine_name='sp_auth_obtener_credenciales')",
                (Config.DB_NAME, Config.DB_NAME),
            )
            tablas, rutinas = cur.fetchone()
            return tablas > 0 and rutinas > 0
    finally:
        con.close()


def instalar_base() -> int:
    """Ejecuta backend.sql completo. OJO: ese script BORRA y recrea la base."""
    if not RUTA_SQL.exists():
        raise FileNotFoundError(f"No encuentro {RUTA_SQL.name} junto a menu.py")
    sentencias = list(dividir_sentencias(RUTA_SQL.read_text(encoding="utf-8-sig")))
    _reiniciar_motor()
    con = _conexion_servidor()
    try:
        with con.cursor() as cur:
            for sql in sentencias:
                try:
                    cur.execute(sql)
                except pymysql.MySQLError as exc:
                    vista = " ".join(sql.split())[:90]
                    raise RuntimeError(f"Falló esta sentencia de backend.sql: {vista}...  ->  {exc}") from exc
    finally:
        con.close()
    return len(sentencias)


# ------------------------------------------------- llamadas a procedimientos
def _leer_resultados(cur) -> List[list]:
    resultados = []
    while True:
        if cur.description is not None:
            resultados.append(list(cur.fetchall()))
        if not cur.nextset():
            break
    return resultados


def llamar(procedimiento: str, *args: Any) -> List[list]:
    """CALL procedimiento(args) y devuelve TODOS los result sets (listas de dicts)."""
    raw = get_engine().raw_connection()
    try:
        cur = raw.cursor(pymysql.cursors.DictCursor)
        try:
            marcas = ", ".join(["%s"] * len(args))
            cur.execute(f"CALL {procedimiento}({marcas})", args)
            return _leer_resultados(cur)
        finally:
            cur.close()
    except Exception:
        try:
            raw.invalidate()      # descarta la conexión por si quedó a medias
        except Exception:
            pass
        raise
    finally:
        raw.close()


def llamar_con_salida(procedimiento: str, *args: Any) -> Any:
    """Procedimientos con UN parámetro OUT al final (p. ej. sp_mesero_crear_pedido)."""
    raw = get_engine().raw_connection()
    try:
        cur = raw.cursor(pymysql.cursors.DictCursor)
        try:
            marcas = ", ".join(["%s"] * len(args) + ["@poli_out"])
            cur.execute(f"CALL {procedimiento}({marcas})", args)
            _leer_resultados(cur)
            cur.execute("SELECT @poli_out AS salida")
            return cur.fetchone()["salida"]
        finally:
            cur.close()
    except Exception:
        try:
            raw.invalidate()
        except Exception:
            pass
        raise
    finally:
        raw.close()
