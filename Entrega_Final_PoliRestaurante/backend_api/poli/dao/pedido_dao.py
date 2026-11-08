"""Pedidos: alta, consulta, cola y cambios de estado/asignación/versionado."""

from ..errores import exigir
from .base import DAO, limite_pagina, pagina_de


class PedidoDAO(DAO):
    def obtener(self, pid):
        return self._requerido("SELECT * FROM pedido WHERE id=?", "pedido", pid)

    def resumen(self, pid):
        return self._uno("SELECT id,estado,version FROM pedido WHERE id=?", (pid,))

    def crear(self, responsable, mesa_id, tipo, fecha):
        return self._insertar(
            "INSERT INTO pedido(responsable_id,mesa_id,tipo,estado,creado,actualizado,version) "
            "VALUES(?,?,?,'PENDIENTE',?,?,1)",
            (responsable, mesa_id, tipo, fecha, fecha),
        )

    def tiene_abiertos(self, uid):
        return self._uno(
            "SELECT id FROM pedido WHERE (responsable_id=? OR cocinero_id=?) "
            "AND estado IN ('PENDIENTE','EN_PREPARACION','LISTO') LIMIT 1",
            (uid, uid),
        ) is not None

    def listar(self, pagina, *, responsable_id=None, estado=None, abiertos=False, ascendente=False):
        q = (
            "SELECT p.*,r.nombre AS responsable,co.nombre AS cocinero,m.numero AS mesa,"
            "COALESCE((SELECT SUM(d.precio_centavos*d.cantidad) FROM detalle d "
            "WHERE d.pedido_id=p.id),0) AS total_centavos FROM pedido p "
            "JOIN usuario r ON r.id=p.responsable_id LEFT JOIN usuario co ON co.id=p.cocinero_id "
            "LEFT JOIN mesa m ON m.id=p.mesa_id WHERE 1=1"
        )
        params = []
        if responsable_id is not None:
            q += " AND p.responsable_id=?"
            params.append(responsable_id)
        if abiertos:
            q += " AND p.estado IN ('PENDIENTE','EN_PREPARACION','LISTO')"
        if estado:
            q += " AND p.estado=?"
            params.append(estado)
        orden = "ASC" if ascendente else "DESC"
        q += f" ORDER BY p.creado {orden},p.id {orden} LIMIT ? OFFSET ?"
        filas = self._filas(q, (*params, *limite_pagina(pagina)))
        for fila in filas:
            fila["total_centavos"] = int(fila["total_centavos"])
        return pagina_de(filas, pagina)

    def cola(self, pagina):
        filas = self._filas(
            "SELECT p.*,r.nombre AS responsable,m.numero AS mesa FROM pedido p "
            "JOIN usuario r ON r.id=p.responsable_id LEFT JOIN mesa m ON m.id=p.mesa_id "
            "WHERE p.estado IN ('PENDIENTE','EN_PREPARACION','LISTO') "
            "ORDER BY p.creado,p.id LIMIT ? OFFSET ?",
            limite_pagina(pagina),
        )
        return pagina_de(filas, pagina)

    def actualizar_version(self, pid, version, fecha):
        filas = self._cambiar(
            "UPDATE pedido SET actualizado=?,version=version+1 WHERE id=? AND version=?",
            (fecha, pid, version),
        )
        exigir(filas == 1, "El pedido cambió; vuelve a consultarlo.", "CONFLICTO")

    def cambiar_estado(self, pid, estado, motivo_cancelacion=None):
        if motivo_cancelacion is not None:
            self._cambiar(
                "UPDATE pedido SET estado=?,motivo_cancelacion=? WHERE id=?",
                (estado, motivo_cancelacion, pid),
            )
        else:
            self._cambiar("UPDATE pedido SET estado=? WHERE id=?", (estado, pid))

    def asignar_responsable(self, pid, uid):
        self._cambiar("UPDATE pedido SET responsable_id=? WHERE id=?", (uid, pid))

    def asignar_cocinero(self, pid, uid):
        self._cambiar("UPDATE pedido SET cocinero_id=? WHERE id=?", (uid, pid))
