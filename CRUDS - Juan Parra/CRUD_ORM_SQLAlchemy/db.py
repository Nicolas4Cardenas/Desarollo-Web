"""Conexión del ORM: engine (conexión) + SessionLocal (fábrica de sesiones)."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from config import Config

# URL.create escapa solo caracteres especiales de la contraseña (@, :, /, *, ...)
URL_BD = URL.create(
    "mysql+pymysql",
    username=Config.DB_USER, password=Config.DB_PASSWORD,
    host=Config.DB_HOST, port=Config.DB_PORT, database=Config.DB_NAME,
    query={"charset": "utf8mb4"},
)
engine = create_engine(URL_BD, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


@contextmanager
def sesion():
    """Transacción explícita: commit si todo sale bien, rollback si algo falla (mejor práctica de la guía)."""
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
