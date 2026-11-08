"""Control de versión y bloqueo de la fila técnica para transacciones MySQL."""

from .base import DAO


class SistemaDAO(DAO):
    def version(self):
        fila = self._uno("SELECT version FROM sistema WHERE id=1")
        return fila["version"] if fila else None

    def bloquear_escritura(self):
        return self._uno("SELECT id FROM sistema WHERE id=1 FOR UPDATE") is not None
