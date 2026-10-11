"""Conexion del ORM (SQLAlchemy). Usa las mismas variables del .env que db.py y el
mismo driver (mysql-connector); la diferencia es que aqui se trabaja con sesiones
y clases en vez de cursores y SQL escrito a mano.

OJO: NO se llama create_all(). Las tablas, triggers y procedimientos las crea
backend.sql; el ORM solo las usa."""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

load_dotenv()

# URL.create escapa bien contrasenas con caracteres especiales (@, :, /, etc.)
url = URL.create(
    "mysql+mysqlconnector",
    username=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "poli_restaurante"),
)

engine = create_engine(url, pool_pre_ping=True)


def get_session():
    """Dependencia de FastAPI: una sesion por peticion. Si el endpoint termina sin
    hacer commit (por ejemplo porque lanzo un error), al cerrar se hace rollback."""
    with Session(engine) as session:
        yield session
