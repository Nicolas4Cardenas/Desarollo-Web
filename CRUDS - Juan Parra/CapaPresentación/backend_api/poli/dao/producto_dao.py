"""Consulta de catálogo requerida por HU02. Precio y categoría salen de la base."""

from ..errores import exigir
from ..validaciones import entero


class ProductoDAO:
    def __init__(self, cursor):
        self.cursor = cursor

    def obtener(self, producto_id):
        entero(producto_id)
        self.cursor.execute(
            "SELECT p.*,c.nombre AS categoria_nombre FROM producto p "
            "JOIN categoria c ON c.id=p.categoria_id WHERE p.id=?",
            (producto_id,),
        )
        producto = self.cursor.one()
        exigir(
            producto is not None,
            f"No existe producto con ID {producto_id}.",
            "NO_EXISTE",
        )
        return producto
