"""Validaciones compartidas. El SQL nunca recibe identificadores arbitrarios."""

from decimal import Decimal, InvalidOperation
import re
from .errores import exigir

ROLES = ("ADMINISTRADOR", "MESERO", "COCINA")
ESTADOS = ("PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO")
ABIERTOS = ESTADOS[:3]


def texto(valor, campo, maximo=100, vacio=False):
    exigir(isinstance(valor, str), f"{campo}: se requiere texto.")
    valor = valor.strip()
    exigir(
        (vacio or valor) and len(valor) <= maximo,
        f"{campo}: longitud de {0 if vacio else 1} a {maximo} caracteres.",
    )
    exigir(
        not any(ord(c) < 32 or ord(c) == 127 for c in valor),
        f"{campo}: no admite saltos de línea ni caracteres de control.",
    )
    return valor


def entero(valor, campo="ID", minimo=1, maximo=2147483647):
    exigir(
        type(valor) is int and minimo <= valor <= maximo,
        f"{campo}: entero entre {minimo} y {maximo}.",
    )
    return valor


def booleano(valor, campo="Activo"):
    exigir(type(valor) is bool, f"{campo}: se requiere verdadero o falso.")
    return int(valor)


def login(valor):
    valor = texto(valor, "Usuario", 40).lower()
    exigir(
        re.fullmatch(r"[a-z0-9_.-]{3,40}", valor) is not None,
        "Usuario: de 3 a 40 letras sin tilde, números, punto, guion o guion bajo.",
    )
    return valor


def clave(valor):
    exigir(
        isinstance(valor, str) and 10 <= len(valor) <= 128,
        "Contraseña: entre 10 y 128 caracteres.",
    )
    exigir(
        valor == valor.strip() and not any(ord(c) < 32 for c in valor),
        "La contraseña no admite espacios en los extremos ni caracteres de control.",
    )
    return valor


def centavos(valor):
    exigir(
        isinstance(valor, (str, int, Decimal)) and not isinstance(valor, bool),
        "Precio: escribe un valor decimal, por ejemplo 18500.00.",
    )
    try:
        d = Decimal(valor)
        exigir(
            d.is_finite() and Decimal("0") < d <= Decimal("99999999.99"),
            "Precio: debe ser positivo y menor o igual a 99999999.99.",
        )
        exigir(d == d.quantize(Decimal("0.01")), "Precio: máximo dos decimales.")
        return int(d * 100)
    except (InvalidOperation, ValueError):
        exigir(False, "Precio inválido.")


def pesos(centavos):
    return "$ " + f"{Decimal(centavos)/100:,.2f}".replace(",", "_").replace(
        ".", ","
    ).replace("_", ".")
