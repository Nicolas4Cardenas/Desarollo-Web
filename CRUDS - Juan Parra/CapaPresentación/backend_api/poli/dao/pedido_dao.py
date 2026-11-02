"""Acceso a pedido y sus detalles. No abre ni confirma conexiones por su cuenta."""

from ..errores import exigir
from ..validaciones import entero


class PedidoDAO:
    def __init__(self, cursor):
        # La conexión pertenece a Base.transaccion, no a cada DAO.
        self.cursor = cursor

    def obtener(self, pedido_id):
        entero(pedido_id)
        self.cursor.execute("SELECT * FROM pedido WHERE id=?", (pedido_id,))
        pedido = self.cursor.one()
        exigir(pedido is not None, f"No existe pedido con ID {pedido_id}.", "NO_EXISTE")
        return pedido

    def contar_detalles(self, pedido_id):
        self.cursor.execute(
            "SELECT COUNT(*) AS n FROM detalle WHERE pedido_id=?", (pedido_id,)
        )
        return self.cursor.one()["n"]

    def insertar_detalle(self, pedido_id, producto, cantidad, notas):
        self.cursor.execute(
            "INSERT INTO detalle(pedido_id,producto_id,categoria_id,producto_nombre,categoria_nombre,precio_centavos,cantidad,notas) VALUES(?,?,?,?,?,?,?,?)",
            (
                pedido_id,
                producto["id"],
                producto["categoria_id"],
                producto["nombre"],
                producto["categoria_nombre"],
                producto["precio_centavos"],
                cantidad,
                notas,
            ),
        )
        return self.cursor.lastrowid

    def actualizar_version(self, pedido_id, version, fecha):
        self.cursor.execute(
            "UPDATE pedido SET actualizado=?,version=version+1 WHERE id=? AND version=?",
            (fecha, pedido_id, version),
        )
        exigir(
            self.cursor.rowcount == 1,
            "El pedido cambió; vuelve a consultarlo.",
            "CONFLICTO",
        )
