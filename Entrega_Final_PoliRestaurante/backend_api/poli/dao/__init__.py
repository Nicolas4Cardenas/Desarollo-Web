"""Acceso a datos: doce DAO de tabla y un DAO de reportes, sin conexiones propias."""

from .auditoria_dao import AuditoriaDAO
from .categoria_dao import CategoriaDAO
from .detalle_dao import DetalleDAO
from .historial_dao import HistorialDAO
from .mesa_dao import MesaDAO
from .ocupacion_dao import OcupacionDAO
from .operacion_dao import OperacionDAO
from .pedido_dao import PedidoDAO
from .producto_dao import ProductoDAO
from .reporte_dao import ReporteDAO
from .sesion_dao import SesionDAO
from .sistema_dao import SistemaDAO
from .usuario_dao import UsuarioDAO

__all__ = [
    "AuditoriaDAO", "CategoriaDAO", "DetalleDAO", "HistorialDAO", "MesaDAO",
    "OcupacionDAO", "OperacionDAO", "PedidoDAO", "ProductoDAO", "ReporteDAO",
    "SesionDAO", "SistemaDAO", "UsuarioDAO",
]
