"""Ciclo de una reserva de mesa: comprobar, reservar y liberar."""

from .base import DAO


class OcupacionDAO(DAO):
    def buscar_por_mesa(self, mesa_id):
        return self._uno("SELECT pedido_id FROM ocupacion WHERE mesa_id=?", (mesa_id,))

    def reservar(self, mesa_id, pedido_id):
        self._cambiar(
            "INSERT INTO ocupacion(mesa_id,pedido_id) VALUES(?,?)", (mesa_id, pedido_id)
        )

    def liberar(self, mesa_id, pedido_id):
        return self._cambiar(
            "DELETE FROM ocupacion WHERE mesa_id=? AND pedido_id=?", (mesa_id, pedido_id)
        )
