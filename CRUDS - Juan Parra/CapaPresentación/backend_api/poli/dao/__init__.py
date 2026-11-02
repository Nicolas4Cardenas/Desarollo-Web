"""DAO = Data Access Object: consultas parametrizadas en la transacción del servicio."""

from .pedido_dao import PedidoDAO
from .producto_dao import ProductoDAO

__all__ = ["PedidoDAO", "ProductoDAO"]
