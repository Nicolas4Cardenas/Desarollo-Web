"""Utilidades comunes de la capa DAO."""
from api.db import conexion


def consumir(cur):
    """Descarta los result sets restantes de un CALL para dejar la conexión limpia."""
    while cur.nextset():
        pass


def conjuntos(cur):
    """Devuelve TODOS los result sets de un CALL como lista de listas."""
    resultado = [list(cur.fetchall())]
    while cur.nextset():
        resultado.append(list(cur.fetchall()))
    return resultado


def mesas_a_lista(texto):
    """'1,2' (GROUP_CONCAT) -> [1, 2]"""
    return [int(m) for m in texto.split(",")] if texto else []


def validar_rol(id_usuario, rol):
    """Llama a sp_validar_rol: lanza ACCESO_DENEGADO si el usuario no tiene ese rol."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_validar_rol(%s, %s)", (id_usuario, rol))
        consumir(cur)


def estado_pedido(id_pedido):
    """Estado actual del pedido o None si no existe (lectura simple, sin reglas)."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("SELECT estado FROM pedido WHERE id_pedido = %s", (id_pedido,))
        fila = cur.fetchone()
        return fila["estado"] if fila else None
