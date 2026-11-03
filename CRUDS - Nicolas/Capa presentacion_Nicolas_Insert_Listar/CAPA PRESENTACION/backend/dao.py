"""DAO = Data Access Object: aqui estan las CONSULTAS a MySQL.

PARA MOSTRAR AL PROFESOR: hay DOS DAO independientes en este archivo.
"""


class PedidoDAO:
    """DAO #1: consulta pedidos de la cola (tabla pedido)."""

    def listar_pendientes(self, db):
        # AQUI ESTA EL PRIMER DAO: SELECT sobre pedido y sus mesas.
        return db.all("""
            SELECT p.id_pedido, p.id_usuario_mesero, p.estado,
                   p.fecha_creacion, fn_total_pedido(p.id_pedido) AS total,
                   (SELECT GROUP_CONCAT(m.numero ORDER BY m.numero)
                      FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa
                     WHERE pm.id_pedido = p.id_pedido) AS mesas
            FROM pedido p
            WHERE p.estado = 'PENDIENTE'
              AND EXISTS (SELECT 1 FROM detalle_pedido d
                          WHERE d.id_pedido = p.id_pedido)
            ORDER BY p.fecha_creacion, p.id_pedido
        """)


class DetallePedidoDAO:
    """DAO #2: consulta productos de los pedidos (detalle_pedido y producto)."""

    def listar_de_pedidos(self, db, ids):
        # AQUI ESTA EL SEGUNDO DAO: SELECT sobre detalle_pedido/producto.
        if not ids:
            return []
        marcadores = ','.join(['%s'] * len(ids))
        return db.all(f"""
            SELECT d.id_pedido, d.id_producto, pr.nombre AS producto,
                   d.cantidad, d.precio_unitario
            FROM detalle_pedido d
            JOIN producto pr ON pr.id_producto = d.id_producto
            WHERE d.id_pedido IN ({marcadores})
            ORDER BY d.id_pedido, d.id_detalle
        """, tuple(ids))
