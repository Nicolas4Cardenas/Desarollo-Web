"""Validación de la entrada (buena práctica de la guía: validar tipos y datos requeridos)."""
from datetime import date, datetime

from flask import request

from api.errores import ErrorNegocio

ESTADOS_PEDIDO = {"PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO"}
FORMATOS_FECHA_HORA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M")


def obtener_json():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorNegocio(400, "JSON_INVALIDO", "El cuerpo debe ser un objeto JSON válido")
    return datos


def entero_positivo(datos, campo):
    valor = datos.get(campo)
    if valor is None:
        raise ErrorNegocio(400, "CAMPO_REQUERIDO", f"El campo '{campo}' es obligatorio")
    return _validar_entero(valor, campo)


def entero_positivo_opcional(datos, campo):
    """Devuelve None si el campo no viene; si viene, debe ser entero > 0."""
    if datos.get(campo) is None:
        return None
    return _validar_entero(datos[campo], campo)


def _validar_entero(valor, campo):
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ErrorNegocio(400, "CAMPO_INVALIDO", f"El campo '{campo}' debe ser un entero mayor que cero")
    return valor


def entero_de_query(nombre):
    """Parámetro opcional de la URL (?id_pedido=3) -> int o None."""
    texto = request.args.get(nombre)
    if texto is None or texto.strip() == "":
        return None
    if not texto.strip().isdigit() or int(texto) <= 0:
        raise ErrorNegocio(400, "CAMPO_INVALIDO", f"El parámetro '{nombre}' debe ser un entero mayor que cero")
    return int(texto)


def estado_valido(valor, campo="estado"):
    if not isinstance(valor, str) or valor.strip().upper() not in ESTADOS_PEDIDO:
        raise ErrorNegocio(
            400, "ESTADO_INVALIDO",
            f"El campo '{campo}' debe ser uno de: " + ", ".join(sorted(ESTADOS_PEDIDO)),
        )
    return valor.strip().upper()


def fecha_de_query(nombre):
    """Parámetro obligatorio de la URL con formato AAAA-MM-DD."""
    texto = request.args.get(nombre)
    if texto is None or texto.strip() == "":
        raise ErrorNegocio(400, "CAMPO_REQUERIDO", f"El parámetro '{nombre}' es obligatorio (AAAA-MM-DD)")
    try:
        return date.fromisoformat(texto.strip())
    except ValueError:
        raise ErrorNegocio(400, "FECHA_INVALIDA", f"El parámetro '{nombre}' debe tener formato AAAA-MM-DD")


def fecha_hora(valor, campo="fecha"):
    """'2026-10-20 14:30:00' (o con 'T') -> datetime."""
    if not isinstance(valor, str):
        raise ErrorNegocio(400, "FECHA_INVALIDA", f"El campo '{campo}' debe ser texto AAAA-MM-DD HH:MM:SS")
    for formato in FORMATOS_FECHA_HORA:
        try:
            return datetime.strptime(valor.strip(), formato)
        except ValueError:
            pass
    raise ErrorNegocio(400, "FECHA_INVALIDA", f"El campo '{campo}' debe tener formato AAAA-MM-DD HH:MM:SS")


def notas_opcionales(datos):
    """Notas: texto, vacío o null; máximo 255 caracteres."""
    notas = datos.get("notas")
    if notas is None:
        return None
    if not isinstance(notas, str):
        raise ErrorNegocio(400, "CAMPO_INVALIDO", "El campo 'notas' debe ser texto")
    notas = notas.strip()
    if len(notas) > 255:
        raise ErrorNegocio(400, "CAMPO_INVALIDO", "El campo 'notas' admite máximo 255 caracteres")
    return notas or None
