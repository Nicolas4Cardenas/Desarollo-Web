"""Consultas de ventas y tiempos. Reciben límites UTC calculados por el servicio."""

from .base import DAO


class ReporteDAO(DAO):
    def ventas_entregadas(self, inicio, fin, categoria_id=None, producto_id=None):
        q = (
            "SELECT p.id AS pedido_id,d.producto_id,d.producto_nombre,d.categoria_nombre,"
            "d.cantidad,d.precio_centavos FROM detalle d JOIN pedido p ON p.id=d.pedido_id "
            "JOIN historial h ON h.pedido_id=p.id AND h.estado='ENTREGADO' "
            "WHERE p.estado='ENTREGADO' AND h.fecha>=? AND h.fecha<?"
        )
        params = [inicio, fin]
        if categoria_id is not None:
            q += " AND d.categoria_id=?"
            params.append(categoria_id)
        if producto_id is not None:
            q += " AND d.producto_id=?"
            params.append(producto_id)
        return self._filas(q, tuple(params))

    def preparaciones(self, inicio, fin):
        return self._filas(
            "SELECT p.id,h1.fecha AS inicio,h2.fecha AS listo FROM pedido p "
            "JOIN historial h1 ON h1.pedido_id=p.id AND h1.estado='EN_PREPARACION' "
            "JOIN historial h2 ON h2.pedido_id=p.id AND h2.estado='LISTO' "
            "WHERE p.estado<>'CANCELADO' AND h2.fecha>=? AND h2.fecha<? ORDER BY p.id",
            (inicio, fin),
        )
