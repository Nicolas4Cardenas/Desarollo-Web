"""Validaciones de entrada compartidas."""
from datetime import date, datetime

from errores import ErrorNegocio

ESTADOS = ("PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO")
FORMATOS_FECHA_HORA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")


def validar_cantidad(cantidad):
    if isinstance(cantidad, bool) or not isinstance(cantidad, int) or cantidad <= 0:
        raise ErrorNegocio("CANTIDAD_INVALIDA", "La cantidad debe ser un entero mayor que cero")
    return cantidad


def limpiar_notas(notas):
    """Texto sin espacios sobrantes; vacío -> None; máximo 255 caracteres."""
    if notas is None:
        return None
    notas = str(notas).strip()
    if len(notas) > 255:
        raise ErrorNegocio("NOTAS_INVALIDAS", "Las notas admiten máximo 255 caracteres")
    return notas or None


def validar_estado(estado):
    if not isinstance(estado, str) or estado.strip().upper() not in ESTADOS:
        raise ErrorNegocio("ESTADO_INVALIDO", "El estado debe ser uno de: " + ", ".join(ESTADOS))
    return estado.strip().upper()


def validar_fecha(valor, campo="fecha"):
    """Acepta date o texto AAAA-MM-DD."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor).strip())
    except ValueError:
        raise ErrorNegocio("FECHA_INVALIDA", f"La {campo} debe tener formato AAAA-MM-DD")


def validar_fecha_hora(valor):
    """Acepta datetime o texto AAAA-MM-DD HH:MM:SS."""
    if isinstance(valor, datetime):
        return valor
    for formato in FORMATOS_FECHA_HORA:
        try:
            return datetime.strptime(str(valor).strip(), formato)
        except ValueError:
            pass
    raise ErrorNegocio("FECHA_INVALIDA", "La fecha debe tener formato AAAA-MM-DD HH:MM:SS")


def validar_rango(desde, hasta):
    desde, hasta = validar_fecha(desde, "fecha inicial"), validar_fecha(hasta, "fecha final")
    if hasta < desde:
        raise ErrorNegocio("RANGO_INVALIDO", "La fecha final no puede ser anterior a la inicial")
    return desde, hasta
