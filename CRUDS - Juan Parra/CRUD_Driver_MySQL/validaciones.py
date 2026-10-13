"""Validaciones de entrada compartidas (HU-02 y HU-03)."""
from errores import ErrorNegocio


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
