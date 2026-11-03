"""El MANAGER coordina DOS DAO en una sola funcionalidad HU-06.

PARA MOSTRAR AL PROFESOR: consultar_cola() invoca a PedidoDAO y
DetallePedidoDAO, ambos con la misma conexion de MySQL (db).
"""
from dao import PedidoDAO, DetallePedidoDAO


class PedidoManager:
    def __init__(self, pedido_dao=None, detalle_dao=None):
        self.pedido_dao = pedido_dao or PedidoDAO()
        self.detalle_dao = detalle_dao or DetallePedidoDAO()

    def consultar_cola(self, db):
        # PASO 1: Manager consulta DAO #1 para LISTAR pedidos pendientes.
        pedidos = self.pedido_dao.listar_pendientes(db)

        # PASO 2: Manager consulta DAO #2 para LISTAR sus productos.
        ids = [p['id_pedido'] for p in pedidos]
        detalles = self.detalle_dao.listar_de_pedidos(db, ids)

        # PASO 3: combina los datos y responde al controlador Flask.
        agrupados = {pid: [] for pid in ids}
        for detalle in detalles:
            agrupados[detalle['id_pedido']].append(detalle)
        return [{**pedido, 'productos': agrupados[pedido['id_pedido']]}
                for pedido in pedidos]
