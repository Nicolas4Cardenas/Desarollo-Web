"""Utilidades de consulta. El cursor pertenece a la transacción que recibe el DAO."""

from ..errores import exigir
from ..validaciones import entero


class DAO:
    def __init__(self, cursor):
        self.cursor = cursor

    def _uno(self, sql, params=()):
        return self.cursor.execute(sql, params).one()

    def _filas(self, sql, params=()):
        return self.cursor.execute(sql, params).all()

    def _insertar(self, sql, params):
        return self.cursor.execute(sql, params).lastrowid

    def _cambiar(self, sql, params):
        return self.cursor.execute(sql, params).rowcount

    def _requerido(self, sql, entidad, ident):
        fila = self._uno(sql, (entero(ident),))
        exigir(fila is not None, f"No existe {entidad} con ID {ident}.", "NO_EXISTE")
        return fila


TAMANO_PAGINA = 50


def pagina_de(filas, numero):
    return {
        "items": filas[:TAMANO_PAGINA],
        "hay_mas": len(filas) > TAMANO_PAGINA,
        "pagina": numero,
    }


def limite_pagina(numero):
    return TAMANO_PAGINA + 1, (numero - 1) * TAMANO_PAGINA
