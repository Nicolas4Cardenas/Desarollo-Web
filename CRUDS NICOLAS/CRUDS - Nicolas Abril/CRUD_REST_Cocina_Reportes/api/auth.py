"""Identificación del usuario que ejecuta la petición.

El backend SQL exige el id del usuario como primer parámetro de cada
procedimiento y valida el rol dentro de la base de datos (RNF-06). Para este
CRUD el cliente envía su id en la cabecera  X-Usuario-Id.
(La autenticación completa con login + JWT corresponde a HU-16.)

Mis HU usan dos roles distintos:
  - cocina (HU-06, 07, 08)          -> X-Usuario-Id: 4   (cocina1)
  - administrador (HU-13, 14, 15)   -> X-Usuario-Id: 1   (admin)
"""
from functools import wraps

from flask import g, request

from api.errores import ErrorNegocio


def requiere_usuario(f):
    @wraps(f)
    def envoltura(*args, **kwargs):
        valor = request.headers.get("X-Usuario-Id")
        if valor is None or not valor.strip().isdigit() or int(valor) <= 0:
            raise ErrorNegocio(
                401, "NO_AUTENTICADO",
                "Falta la cabecera X-Usuario-Id con el id del usuario (entero positivo)",
            )
        g.id_usuario = int(valor)
        return f(*args, **kwargs)

    return envoltura
