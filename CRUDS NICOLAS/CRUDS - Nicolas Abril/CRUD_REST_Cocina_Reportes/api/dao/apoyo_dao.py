"""Funciones de APOYO de otras HU (mesero / admin) para que mi parte funcione completa:
crear pedido (HU-01), agregar productos (HU-02), entregar (HU-04), cancelar (HU-05) y consultas."""
from api.dao.comun import conjuntos, consumir, mesas_a_lista
from api.db import conexion


def _normalizar(fila):
    fila["mesas"] = mesas_a_lista(fila.get("mesas"))
    return fila


# ---------------------------------------------------------------- lecturas
def listar_menu(id_usuario):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_listar_menu(%s)", (id_usuario,))
        return conjuntos(cur)[0]


def listar_mesas_libres(id_usuario):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_listar_mesas_libres(%s)", (id_usuario,))
        return conjuntos(cur)[0]


def listar_pedidos(id_admin, estado=None):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_listar_pedidos(%s, %s)", (id_admin, estado))
        return [_normalizar(f) for f in conjuntos(cur)[0]]


def obtener_pedido(id_admin, id_pedido):
    """Pedido + productos, o None si no existe."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_ver_pedido(%s, %s)", (id_admin, id_pedido))
        r = conjuntos(cur)
        if not r[0]:
            return None
        pedido = _normalizar(r[0][0])
        pedido["productos"] = r[1] if len(r) > 1 else []
        return pedido


# -------------------------------------------------------------- escrituras
def crear_pedido(id_mesero, id_mesa):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_crear_pedido(%s, %s, @id_pedido)", (id_mesero, id_mesa))
        consumir(cur)
        cur.execute("SELECT @id_pedido AS id_pedido")
        return cur.fetchone()["id_pedido"]


def agregar_producto(id_mesero, id_pedido, id_producto, cantidad, notas):
    """Devuelve {'id_pedido', 'total', 'id_detalle'}."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_agregar_producto(%s, %s, %s, %s, %s)",
                    (id_mesero, id_pedido, id_producto, cantidad, notas))
        resultado = cur.fetchone()
        consumir(cur)
        cur.execute("SELECT id_detalle FROM detalle_pedido WHERE id_pedido = %s AND id_producto = %s",
                    (id_pedido, id_producto))
        resultado["id_detalle"] = cur.fetchone()["id_detalle"]
        return resultado


def marcar_entregado(id_mesero, id_pedido):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_marcar_entregado(%s, %s)", (id_mesero, id_pedido))
        consumir(cur)


def cancelar_pedido(id_mesero, id_pedido):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_mesero_cancelar_pedido(%s, %s)", (id_mesero, id_pedido))
        consumir(cur)
