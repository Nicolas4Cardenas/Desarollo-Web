"""Recibos de idempotencia consultables únicamente por el usuario propietario."""

from .base import DAO


class OperacionDAO(DAO):
    def buscar(self, uid, clave):
        return self._uno(
            "SELECT huella,resultado,fecha FROM operacion WHERE usuario_id=? AND clave=?",
            (uid, clave),
        )

    def registrar(self, uid, clave, huella, resultado, fecha):
        return self._insertar(
            "INSERT INTO operacion(usuario_id,clave,huella,resultado,fecha) VALUES(?,?,?,?,?)",
            (uid, clave, huella, resultado, fecha),
        )
