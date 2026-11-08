"""Líneas del pedido con instantánea histórica del precio y la categoría."""

from .base import DAO


class DetalleDAO(DAO):
    def obtener(self, did):
        return self._requerido("SELECT * FROM detalle WHERE id=?", "detalle", did)

    def listar(self, pid):
        return self._filas("SELECT * FROM detalle WHERE pedido_id=? ORDER BY id", (pid,))

    def contar(self, pid):
        return self._uno("SELECT COUNT(*) AS n FROM detalle WHERE pedido_id=?", (pid,))["n"]

    def tiene_lineas(self, pid):
        return self._uno("SELECT id FROM detalle WHERE pedido_id=? LIMIT 1", (pid,)) is not None

    def usa_categoria(self, cid):
        return self._uno("SELECT id FROM detalle WHERE categoria_id=? LIMIT 1", (cid,)) is not None

    def total(self, pid):
        return int(self._uno(
            "SELECT COALESCE(SUM(precio_centavos*cantidad),0) AS total FROM detalle WHERE pedido_id=?",
            (pid,),
        )["total"])

    def crear(self, pid, producto, cantidad, notas):
        return self._insertar(
            "INSERT INTO detalle(pedido_id,producto_id,categoria_id,producto_nombre,"
            "categoria_nombre,precio_centavos,cantidad,notas) VALUES(?,?,?,?,?,?,?,?)",
            (
                pid, producto["id"], producto["categoria_id"], producto["nombre"],
                producto["categoria_nombre"], producto["precio_centavos"], cantidad, notas,
            ),
        )

    def actualizar(self, did, cantidad, notas):
        self._cambiar(
            "UPDATE detalle SET cantidad=?,notas=? WHERE id=?", (cantidad, notas, did)
        )

    def eliminar(self, did):
        self._cambiar("DELETE FROM detalle WHERE id=?", (did,))
