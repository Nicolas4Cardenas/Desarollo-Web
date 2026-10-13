"""Capa de acceso a datos (DAO) del módulo MESERO.

No contiene reglas de negocio: todas viven en los procedimientos almacenados
del backend.sql (que validan rol, dueño del pedido, estado y transacciones).
Este módulo solo los invoca con CALL y devuelve los resultados como dict/list.
Los errores de la base de datos se propagan y api/errores.py los traduce a HTTP.
"""
from api.db import conexion
from api.errores import ErrorNegocio


def _consumir(cur):
    """Descarta los result sets restantes de un CALL para dejar la conexión limpia."""
    while cur.nextset():
        pass


def _normalizar_pedido(fila):
    """'mesas' llega como texto '1,2' desde GROUP_CONCAT -> lista de enteros."""
    mesas = fila.get("mesas")
    fila["mesas"] = [int(m) for m in mesas.split(",")] if mesas else []
    return fila


# ---------------------------------------------------------------- lecturas
def listar_menu(id_usuario):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_listar_menu(%s)", (id_usuario,))
        filas = cur.fetchall()
        _consumir(cur)
        return filas


def listar_mesas_libres(id_usuario):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_listar_mesas_libres(%s)", (id_usuario,))
        filas = cur.fetchall()
        _consumir(cur)
        return filas


def listar_pedidos(id_usuario, estado=None):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_mis_pedidos(%s, %s)", (id_usuario, estado))
        filas = cur.fetchall()
        _consumir(cur)
        return [_normalizar_pedido(f) for f in filas]


def obtener_pedido(id_usuario, id_pedido):
    """Pedido + sus productos. Devuelve None si no existe o es de otro mesero."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_ver_pedido(%s, %s)", (id_usuario, id_pedido))
        pedidos = cur.fetchall()
        productos = []
        if cur.nextset():
            productos = cur.fetchall()
        _consumir(cur)
        if not pedidos:
            return None
        pedido = _normalizar_pedido(pedidos[0])
        pedido["productos"] = list(productos)
        return pedido


def _validar_mesero(cur, id_usuario):
    cur.execute("CALL sp_validar_rol(%s, 'MESERO')", (id_usuario,))
    _consumir(cur)


def obtener_detalle(id_usuario, id_pedido, id_detalle):
    """Renglón del pedido (id_detalle, id_producto, cantidad, notas) o None."""
    with conexion() as con, con.cursor() as cur:
        _validar_mesero(cur, id_usuario)
        cur.execute(
            "SELECT id_detalle, id_producto, cantidad, notas "
            "FROM detalle_pedido WHERE id_detalle = %s AND id_pedido = %s",
            (id_detalle, id_pedido),
        )
        return cur.fetchone()


# ---------------------------------------------------------------- escrituras
def crear_pedido(id_usuario, id_mesa):
    """HU-01"""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_crear_pedido(%s, %s, @id_pedido)", (id_usuario, id_mesa))
        _consumir(cur)
        cur.execute("SELECT @id_pedido AS id_pedido")
        return cur.fetchone()["id_pedido"]


def agregar_producto(id_usuario, id_pedido, id_producto, cantidad, notas):
    """HU-02. Devuelve {'id_pedido', 'total', 'id_detalle'}."""
    with conexion() as con, con.cursor() as cur:
        cur.execute(
            "CALL sp_mesero_agregar_producto(%s, %s, %s, %s, %s)",
            (id_usuario, id_pedido, id_producto, cantidad, notas),
        )
        resultado = cur.fetchone()
        _consumir(cur)
        cur.execute(
            "SELECT id_detalle FROM detalle_pedido WHERE id_pedido = %s AND id_producto = %s",
            (id_pedido, id_producto),
        )
        resultado["id_detalle"] = cur.fetchone()["id_detalle"]
        return resultado


def modificar_detalle(id_usuario, id_detalle, cantidad, notas):
    """HU-03 (editar). Devuelve {'id_pedido', 'total'}."""
    with conexion() as con, con.cursor() as cur:
        cur.execute(
            "CALL sp_mesero_modificar_detalle(%s, %s, %s, %s)",
            (id_usuario, id_detalle, cantidad, notas),
        )
        resultado = cur.fetchone()
        _consumir(cur)
        return resultado


def quitar_producto(id_usuario, id_detalle):
    """HU-03 (quitar). Devuelve {'id_pedido', 'total'}."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_quitar_producto(%s, %s)", (id_usuario, id_detalle))
        resultado = cur.fetchone()
        _consumir(cur)
        return resultado


def marcar_entregado(id_usuario, id_pedido):
    """HU-04"""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_marcar_entregado(%s, %s)", (id_usuario, id_pedido))
        _consumir(cur)


def cancelar_pedido(id_usuario, id_pedido):
    """HU-05"""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_cancelar_pedido(%s, %s)", (id_usuario, id_pedido))
        _consumir(cur)
