"""Persistencia de cuentas. Las lecturas de administración excluyen hashes."""

from .base import DAO


class UsuarioDAO(DAO):
    def contar(self):
        return self._uno("SELECT COUNT(*) AS n FROM usuario")["n"]

    def contar_administradores_activos(self):
        return self._uno(
            "SELECT COUNT(*) AS n FROM usuario WHERE activo=1 AND rol='ADMINISTRADOR'"
        )["n"]

    def buscar_login(self, login):
        return self._uno("SELECT * FROM usuario WHERE login=?", (login,))

    def obtener(self, uid):
        return self._requerido("SELECT * FROM usuario WHERE id=?", "usuario", uid)

    def buscar_identidad(self, uid):
        return self._uno("SELECT id,login,rol,activo FROM usuario WHERE id=?", (uid,))

    def listar(self):
        return self._filas(
            "SELECT id,nombre,login,rol,activo,debe_cambiar,bloqueado_hasta "
            "FROM usuario ORDER BY id"
        )

    def crear(self, nombre, login, hash_password, rol, activo=True, temporal=False):
        return self._insertar(
            "INSERT INTO usuario(nombre,login,password_hash,rol,activo,debe_cambiar) "
            "VALUES(?,?,?,?,?,?)",
            (nombre, login, hash_password, rol, activo, temporal),
        )

    def actualizar(self, uid, nombre, login, rol, activo):
        self._cambiar(
            "UPDATE usuario SET nombre=?,login=?,rol=?,activo=? WHERE id=?",
            (nombre, login, rol, activo, uid),
        )

    def desactivar(self, uid):
        self._cambiar("UPDATE usuario SET activo=0 WHERE id=?", (uid,))

    def registrar_intentos(self, uid, fallos=0, bloqueo=None):
        self._cambiar(
            "UPDATE usuario SET fallos=?,bloqueado_hasta=? WHERE id=?",
            (fallos, bloqueo, uid),
        )

    def cambiar_clave(self, uid, hash_password, temporal=False):
        self._cambiar(
            "UPDATE usuario SET password_hash=?,debe_cambiar=?,fallos=0,bloqueado_hasta=NULL "
            "WHERE id=?",
            (hash_password, temporal, uid),
        )
