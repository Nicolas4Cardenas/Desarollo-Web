"""Sesiones: registra y revoca huellas, nunca guarda el token original."""

from .base import DAO


class SesionDAO(DAO):
    def buscar_actor(self, token_hash):
        return self._uno(
            "SELECT u.id,u.nombre,u.login,u.rol,u.activo,u.debe_cambiar,s.expira "
            "FROM sesion s JOIN usuario u ON u.id=s.usuario_id WHERE s.token_hash=?",
            (token_hash,),
        )

    def crear(self, token_hash, usuario_id, creado, expira):
        self._cambiar(
            "INSERT INTO sesion(token_hash,usuario_id,creado,expira) VALUES(?,?,?,?)",
            (token_hash, usuario_id, creado, expira),
        )

    def purgar_vencidas(self, ahora):
        self._cambiar("DELETE FROM sesion WHERE expira<=?", (ahora,))

    def revocar(self, token_hash):
        self._cambiar("DELETE FROM sesion WHERE token_hash=?", (token_hash,))

    def revocar_usuario(self, usuario_id):
        self._cambiar("DELETE FROM sesion WHERE usuario_id=?", (usuario_id,))
