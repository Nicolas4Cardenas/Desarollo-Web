"""Catálogo y datos de precio/categoría que HU02 copia a su línea de pedido."""

from .base import DAO


class ProductoDAO(DAO):
    def obtener(self, producto_id):
        return self._requerido(
            "SELECT p.*,c.nombre AS categoria_nombre FROM producto p "
            "JOIN categoria c ON c.id=p.categoria_id WHERE p.id=?",
            "producto",
            producto_id,
        )

    def listar(self, incluir_archivados=False):
        filtro = "" if incluir_archivados else " WHERE p.activo=1 AND p.disponible=1"
        return self._filas(
            "SELECT p.*,ca.nombre AS categoria FROM producto p "
            "JOIN categoria ca ON ca.id=p.categoria_id"
            + filtro + " ORDER BY ca.nombre,p.nombre,p.id"
        )

    def buscar_nombre(self, nombre):
        return self._uno("SELECT id FROM producto WHERE nombre=? LIMIT 1", (nombre,))

    def usa_categoria(self, cid):
        return self._uno("SELECT id FROM producto WHERE categoria_id=? LIMIT 1", (cid,)) is not None

    def crear(self, nombre, descripcion, precio, categoria_id, disponible=True, activo=True):
        return self._insertar(
            "INSERT INTO producto(nombre,descripcion,precio_centavos,categoria_id,disponible,activo) "
            "VALUES(?,?,?,?,?,?)",
            (nombre, descripcion, precio, categoria_id, disponible, activo),
        )

    def actualizar(self, pid, nombre, descripcion, precio, categoria_id, disponible, activo):
        self._cambiar(
            "UPDATE producto SET nombre=?,descripcion=?,precio_centavos=?,categoria_id=?,"
            "disponible=?,activo=? WHERE id=?",
            (nombre, descripcion, precio, categoria_id, disponible, activo, pid),
        )

    def archivar(self, pid):
        self._cambiar("UPDATE producto SET activo=0,disponible=0 WHERE id=?", (pid,))
