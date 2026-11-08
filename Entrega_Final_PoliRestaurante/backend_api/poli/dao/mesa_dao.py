"""Mesas de salón y consulta de su ocupación actual."""

from .base import DAO


class MesaDAO(DAO):
    def obtener(self, mid):
        return self._requerido("SELECT * FROM mesa WHERE id=?", "mesa", mid)

    def buscar_numero(self, numero):
        return self._uno("SELECT id FROM mesa WHERE numero=?", (numero,))

    def listar(self, incluir_archivadas=False):
        filtro = "" if incluir_archivadas else " WHERE m.activa=1"
        return self._filas(
            "SELECT m.*,CASE WHEN o.pedido_id IS NULL THEN 'LIBRE' ELSE 'OCUPADA' END "
            "AS estado,o.pedido_id FROM mesa m LEFT JOIN ocupacion o ON o.mesa_id=m.id"
            + filtro + " ORDER BY m.numero"
        )

    def crear(self, numero, capacidad, activa=True):
        return self._insertar(
            "INSERT INTO mesa(numero,capacidad,activa) VALUES(?,?,?)",
            (numero, capacidad, activa),
        )

    def actualizar(self, mid, numero, capacidad, activa):
        self._cambiar(
            "UPDATE mesa SET numero=?,capacidad=?,activa=? WHERE id=?",
            (numero, capacidad, activa, mid),
        )

    def archivar(self, mid):
        self._cambiar("UPDATE mesa SET activa=0 WHERE id=?", (mid,))
