"""Diagnóstico sin conexión a Internet y sin crear tablas ni archivos de datos."""

import sys
import sqlite3
import hashlib
from pathlib import Path

print("Python:", sys.version.split()[0])
print("SQLite:", sqlite3.sqlite_version)
print("Carpeta:", Path(__file__).resolve().parent)
if sys.version_info < (3, 10):
    raise SystemExit("Se requiere Python 3.10 o posterior.")
assert hashlib.pbkdf2_hmac("sha256", b"a", b"b", 1000)
with sqlite3.connect(":memory:") as c:
    c.execute("CREATE TABLE verificacion(id INTEGER PRIMARY KEY)")
    c.execute("INSERT INTO verificacion VALUES(1)")
    assert c.execute("SELECT id FROM verificacion").fetchone()[0] == 1
print("Modo SQLite disponible. No necesita instalar paquetes de pip.")
print("La carpeta del proyecto debe permitir guardar el archivo de datos.")
