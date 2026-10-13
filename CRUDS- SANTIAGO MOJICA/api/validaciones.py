"""Validación de la entrada (buena práctica de la guía: validar tipos y datos requeridos)."""
from flask import request

from api.errores import ErrorNegocio

ESTADOS_PEDIDO = {"PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO"}


def obtener_json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorNegocio(400, "JSON_INVALIDO", "El cuerpo debe ser un objeto JSON válido")
    return datos


def entero_positivo(datos, campo):
    valor = datos.get(campo)
    if valor is None:
        raise ErrorNegocio(400, "CAMPO_REQUERIDO", f"El campo '{campo}' es obligatorio")
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErrorNegocio(400, "CAMPO_INVALIDO", f"El campo '{campo}' debe ser un entero mayor que cero")
    return valor


def notas_opcionales(datos):
    """Devuelve (presente, valor). Las notas pueden ser texto, vacío o null."""
    if "notas" not in datos:
        return False, None
    notas = datos["notas"]
    if notas is None:
        return True, None
    if not isinstance(notas, str):
        raise ErrorNegocio(400, "CAMPO_INVALIDO", "El campo 'notas' debe ser texto")
    notas = notas.strip()
    if len(notas) > 255:
        raise ErrorNegocio(400, "CAMPO_INVALIDO", "El campo 'notas' admite máximo 255 caracteres")
    return True, (notas or None)
