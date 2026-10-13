"""Flujo principal: prepara la base, inicia sesión y abre el menú del rol."""
import sys

from . import admin, auth, cocina, db, mesero, ui
from .errores import mensaje_error


def _preparar_base() -> None:
    """Si la base no existe, la crea ejecutando backend.sql (todo automático)."""
    if db.base_instalada():
        return
    ui.info("No encontré la base 'poli_restaurante'. Creándola desde backend.sql ...")
    n = db.instalar_base()
    ui.ok(f"Base de datos lista ({n} sentencias ejecutadas, con datos de ejemplo).")
    ui.pausar()


def _iniciar_sesion() -> None:
    s = auth.iniciar_sesion()
    if s is None:
        ui.error("Demasiados intentos fallidos.")
        return
    ui.ok(f"Bienvenido, {s.nombre} ({s.rol}).")
    ui.pausar()
    if s.rol == "MESERO":
        mesero.menu(s)
    elif s.rol == "COCINA":
        cocina.menu(s)
    elif s.rol == "ADMINISTRADOR":
        admin.menu(s)
    else:
        ui.error(f"Rol sin menú disponible: {s.rol}")


def _reinstalar() -> None:
    ui.aviso("Esto BORRA toda la base 'poli_restaurante' y la vuelve a crear con los datos de ejemplo.")
    if ui.leer_texto("Escribe BORRAR para confirmar") != "BORRAR":
        ui.info("No se hizo ningún cambio.")
        return
    n = db.instalar_base()
    ui.ok(f"Base de datos reinstalada ({n} sentencias).")


def main() -> None:
    try:
        _preparar_base()
    except Exception as exc:  # noqa: BLE001
        ui.error(mensaje_error(exc) or f"{type(exc).__name__}: {exc}")
        print("\nRevisa que MySQL/MariaDB esté encendido. Si tu usuario o clave no son "
              "root/12345, copia .env.example a .env y ajústalos.")
        sys.exit(1)

    ui.menu("POLI RESTAURANTE", [
        ("Iniciar sesión", lambda: _iniciar_sesion()),
        ("Reinstalar base de datos (borra todo)", lambda: _reinstalar()),
    ], salida="Salir",
        subtitulo="Demo: admin / Admin2026*   mesero1 / Mesero2026*   cocina1 / Cocina2026*")
    print("¡Hasta luego!")
