"""Punto de entrada:  python menu.py"""
import importlib
import subprocess
import sys
from pathlib import Path

DEPENDENCIAS = (
    ("sqlalchemy", "SQLAlchemy>=2.0"),
    ("pymysql", "PyMySQL>=1.1"),
    ("bcrypt", "bcrypt>=4.0"),
    ("dotenv", "python-dotenv>=1.0"),
)


def asegurar_dependencias() -> None:
    """Si falta alguna librería, intenta instalarla automáticamente."""
    faltan = []
    for modulo, paquete in DEPENDENCIAS:
        try:
            importlib.import_module(modulo)
        except ImportError:
            faltan.append(paquete)
    if not faltan:
        return
    print("Instalando dependencias:", ", ".join(faltan))
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *faltan])
    except subprocess.CalledProcessError:
        req = Path(__file__).with_name("requirements.txt")
        print("\nNo pude instalar las dependencias automáticamente.")
        print(f"Ejecuta manualmente:  pip install -r {req.name}")
        sys.exit(1)


if __name__ == "__main__":
    asegurar_dependencias()
    from poli.app import main

    main()
