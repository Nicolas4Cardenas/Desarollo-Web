"""Altas, consultas, cambios de nombre y retiro de categorías."""

from .base import DAO


class CategoriaDAO(DAO):
    def listar(self):
        return self._filas("SELECT id,nombre FROM categoria ORDER BY nombre")

    def obtener(self, cid):
        return self._requerido("SELECT * FROM categoria WHERE id=?", "categoria", cid)

    def buscar_nombre(self, nombre):
        return self._uno("SELECT id FROM categoria WHERE nombre=?", (nombre,))

    def crear(self, nombre):
        return self._insertar("INSERT INTO categoria(nombre) VALUES(?)", (nombre,))

    def actualizar(self, cid, nombre):
        self._cambiar("UPDATE categoria SET nombre=? WHERE id=?", (nombre, cid))

    def eliminar(self, cid):
        self._cambiar("DELETE FROM categoria WHERE id=?", (cid,))
