"""Capa de acceso a datos del módulo COCINA (HU-06, HU-07, HU-08).

No contiene reglas de negocio: viven en los procedimientos almacenados
(sp_cocina_*), que validan el rol COCINA, que el pedido tenga productos y que
la transición de estado sea válida (y registran el historial).
"""
from api.dao.comun import conjuntos, consumir, mesas_a_lista
from api.db import conexion


def _armar_pedidos(pedidos, productos):
    """Une el result set de pedidos con el de productos (por id_pedido)."""
    por_pedido = {}
    for p in productos:
        por_pedido.setdefault(p["id_pedido"], []).append(
            {"producto": p["producto"], "cantidad": p["cantidad"], "notas": p["notas"]})
    for ped in pedidos:
        ped["mesas"] = mesas_a_lista(ped.get("mesas"))
        ped["productos"] = por_pedido.get(ped["id_pedido"], [])
    return pedidos


def ver_cola(id_usuario):
    """HU-06: pedidos PENDIENTES (con productos), del más antiguo al más reciente."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_cocina_ver_cola(%s)", (id_usuario,))
        r = conjuntos(cur)
        return _armar_pedidos(r[0], r[1] if len(r) > 1 else [])


def ver_en_preparacion(id_usuario):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_cocina_ver_en_preparacion(%s)", (id_usuario,))
        r = conjuntos(cur)
        return _armar_pedidos(r[0], r[1] if len(r) > 1 else [])


def iniciar_preparacion(id_usuario, id_pedido):
    """HU-07: PENDIENTE -> EN_PREPARACION"""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_cocina_iniciar_preparacion(%s, %s)", (id_usuario, id_pedido))
        consumir(cur)


def marcar_listo(id_usuario, id_pedido):
    """HU-08: EN_PREPARACION -> LISTO"""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_cocina_marcar_listo(%s, %s)", (id_usuario, id_pedido))
        consumir(cur)
