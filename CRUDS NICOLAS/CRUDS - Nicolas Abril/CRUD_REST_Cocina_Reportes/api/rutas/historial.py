"""Rutas REST del HISTORIAL de estados (HU-15) — CRUD completo. Requiere usuario ADMINISTRADOR.

  GET    /historial[?id_pedido=N]     listar (todos o los de un pedido)      READ
  GET    /historial/<id>              ver un registro                        READ
  POST   /historial                   crear un registro                      CREATE
  PUT    /historial/<id>              editar estado / fecha / usuario        UPDATE
  DELETE /historial/<id>              eliminar un registro                   DELETE
"""
from flask import Blueprint, g, jsonify, url_for

from api.auth import requiere_usuario
from api.dao import historial_dao
from api.errores import ErrorNegocio
from api.validaciones import (entero_de_query, entero_positivo, entero_positivo_opcional,
                              estado_valido, fecha_hora, obtener_json)

bp = Blueprint("historial", __name__, url_prefix="/api/v1")


def _registro_o_404(id_historial):
    registro = historial_dao.obtener(g.id_usuario, id_historial)
    if registro is None:
        raise ErrorNegocio(404, "HISTORIAL_NO_EXISTE", "El registro de historial no existe")
    return registro


@bp.get("/historial")
@requiere_usuario
def listar_historial():
    registros = historial_dao.listar(g.id_usuario, entero_de_query("id_pedido"))
    return jsonify({"total": len(registros), "historial": registros}), 200


@bp.get("/historial/<int:id_historial>")
@requiere_usuario
def ver_historial(id_historial):
    return jsonify(_registro_o_404(id_historial)), 200


@bp.post("/historial")
@requiere_usuario
def crear_historial():
    datos = obtener_json()
    id_pedido = entero_positivo(datos, "id_pedido")
    if datos.get("estado") is None:
        raise ErrorNegocio(400, "CAMPO_REQUERIDO", "El campo 'estado' es obligatorio")
    estado = estado_valido(datos["estado"])
    fecha = fecha_hora(datos["fecha"]) if datos.get("fecha") is not None else None
    id_usuario_cambio = entero_positivo_opcional(datos, "id_usuario_cambio")
    id_historial = historial_dao.crear(g.id_usuario, id_pedido, estado, fecha, id_usuario_cambio)
    respuesta = jsonify({
        "mensaje": "Registro de historial creado",
        "registro": _registro_o_404(id_historial),
    })
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for("historial.ver_historial", id_historial=id_historial)
    return respuesta


@bp.put("/historial/<int:id_historial>")
@requiere_usuario
def editar_historial(id_historial):
    datos = obtener_json()
    estado = estado_valido(datos["estado"]) if datos.get("estado") is not None else None
    fecha = fecha_hora(datos["fecha"]) if datos.get("fecha") is not None else None
    id_usuario_cambio = entero_positivo_opcional(datos, "id_usuario_cambio")
    if estado is None and fecha is None and id_usuario_cambio is None:
        raise ErrorNegocio(400, "CAMPO_REQUERIDO",
                           "Envíe al menos uno de: estado, fecha, id_usuario_cambio")
    _registro_o_404(id_historial)
    historial_dao.editar(g.id_usuario, id_historial, estado, fecha, id_usuario_cambio)
    return jsonify({"mensaje": "Registro de historial actualizado",
                    "registro": _registro_o_404(id_historial)}), 200


@bp.delete("/historial/<int:id_historial>")
@requiere_usuario
def eliminar_historial(id_historial):
    _registro_o_404(id_historial)
    historial_dao.eliminar(g.id_usuario, id_historial)
    return jsonify({"mensaje": "Registro de historial eliminado", "id_historial": id_historial}), 200
