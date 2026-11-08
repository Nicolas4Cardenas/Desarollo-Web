"""Historial de cambios de estado: solo inserción y consulta."""

from .base import DAO


class HistorialDAO(DAO):
    def registrar(self, pid, estado, usuario_id, fecha, motivo):
        return self._insertar(
            "INSERT INTO historial(pedido_id,estado,usuario_id,fecha,motivo) VALUES(?,?,?,?,?)",
            (pid, estado, usuario_id, fecha, motivo),
        )

    def listar_pedido(self, pid):
        return self._filas(
            "SELECT h.*,u.nombre AS usuario FROM historial h JOIN usuario u ON u.id=h.usuario_id "
            "WHERE pedido_id=? ORDER BY h.id",
            (pid,),
        )
