"""Traduce errores de MySQL/SQLAlchemy a mensajes legibles."""
from typing import Optional


def mensaje_error(exc: BaseException) -> Optional[str]:
    """Devuelve un mensaje amigable, o None si el error no es de base de datos."""
    try:
        import pymysql
    except ImportError:  # pragma: no cover
        return None

    orig = getattr(exc, "orig", exc)          # SQLAlchemy envuelve el error real en .orig
    if not isinstance(orig, pymysql.MySQLError):
        return None

    codigo = orig.args[0] if orig.args and isinstance(orig.args[0], int) else None
    texto = str(orig.args[1]) if len(orig.args) > 1 else str(orig)

    if codigo == 1644:                         # SIGNAL SQLSTATE '45000' del backend
        humano = texto.split(": ", 1)[1] if ": " in texto else texto
        return humano[:1].upper() + humano[1:]
    if codigo in (2002, 2003, 2006, 2013):
        return ("No hay conexión con el servidor MySQL. Verifica que esté encendido "
                "y que host/puerto en tu .env sean correctos.")
    if codigo == 1045:
        return "MySQL rechazó el usuario o la contraseña. Revisa DB_USER y DB_PASSWORD en tu .env."
    if codigo in (3819, 4025):
        return "El dato no cumple una restricción de la base de datos."
    if codigo == 1062:
        return "Ya existe un registro con ese valor único."
    if codigo == 1451:
        return "No se puede eliminar: otros registros dependen de este."
    return f"Error de base de datos ({codigo}): {texto}"
