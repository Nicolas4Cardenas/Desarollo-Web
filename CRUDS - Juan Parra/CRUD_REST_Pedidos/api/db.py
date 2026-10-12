"""Conexión a MySQL (capa de persistencia).

Cada petición abre su propia conexión y la cierra al terminar: el servicio es
stateless (principio REST). Las transacciones las manejan los procedimientos
almacenados del backend.sql (RNF-10), por eso se usa autocommit.
"""
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from config import Config


@contextmanager
def conexion():
    con = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    try:
        yield con
    finally:
        con.close()
