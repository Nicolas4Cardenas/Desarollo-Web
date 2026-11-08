"""Registro de acciones administrativas, de acceso y de operación."""

from .base import DAO, limite_pagina, pagina_de


class AuditoriaDAO(DAO):
    def registrar(self, uid, accion, entidad, eid, fecha, descripcion):
        return self._insertar(
            "INSERT INTO auditoria(usuario_id,accion,entidad,entidad_id,fecha,descripcion) "
            "VALUES(?,?,?,?,?,?)",
            (uid, accion, entidad, eid, fecha, descripcion),
        )

    def buscar_primera_accion(self, accion):
        return self._uno(
            "SELECT descripcion FROM auditoria WHERE accion=? ORDER BY id LIMIT 1", (accion,)
        )

    def listar(self, pagina):
        filas = self._filas(
            "SELECT a.*,u.login AS usuario FROM auditoria a JOIN usuario u ON u.id=a.usuario_id "
            "ORDER BY a.id DESC LIMIT ? OFFSET ?",
            limite_pagina(pagina),
        )
        return pagina_de(filas, pagina)
