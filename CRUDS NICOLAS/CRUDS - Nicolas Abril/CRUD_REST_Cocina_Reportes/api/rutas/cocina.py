"""Rutas REST del módulo COCINA (HU-06, HU-07, HU-08). Requiere usuario con rol COCINA.

  HU-06  GET  /cocina/cola                        ver cola de pedidos pendientes
  (HU-07) GET /cocina/en-preparacion              ver lo que está en preparación
  HU-07  PUT  /cocina/pedidos/<id>/preparar       PENDIENTE -> EN_PREPARACION
  HU-08  PUT  /cocina/pedidos/<id>/listo          EN_PREPARACION -> LISTO
"""
from flask import Blueprint, g, jsonify

from api.auth import requiere_usuario
from api.dao import cocina_dao
from api.dao.comun import estado_pedido, validar_rol
from api.errores import ErrorNegocio

bp = Blueprint("cocina", __name__, url_prefix="/api/v1/cocina")


def _existe_o_404(id_pedido):
    estado = estado_pedido(id_pedido)
    if estado is None:
        raise ErrorNegocio(404, "PEDIDO_NO_EXISTE", "El pedido indicado no existe")
    return estado


@bp.get("/cola")
@requiere_usuario
def ver_cola():
    pedidos = cocina_dao.ver_cola(g.id_usuario)
    return jsonify({"total": len(pedidos), "pedidos": pedidos}), 200


@bp.get("/en-preparacion")
@requiere_usuario
def ver_en_preparacion():
    pedidos = cocina_dao.ver_en_preparacion(g.id_usuario)
    return jsonify({"total": len(pedidos), "pedidos": pedidos}), 200


@bp.put("/pedidos/<int:id_pedido>/preparar")
@requiere_usuario
def iniciar_preparacion(id_pedido):
    validar_rol(g.id_usuario, "COCINA")          # el rol se revisa antes de revelar si el pedido existe
    _existe_o_404(id_pedido)
    cocina_dao.iniciar_preparacion(g.id_usuario, id_pedido)
    return jsonify({
        "mensaje": "Pedido en preparación",
        "id_pedido": id_pedido,
        "estado": estado_pedido(id_pedido),
    }), 200


@bp.put("/pedidos/<int:id_pedido>/listo")
@requiere_usuario
def marcar_listo(id_pedido):
    validar_rol(g.id_usuario, "COCINA")
    _existe_o_404(id_pedido)
    cocina_dao.marcar_listo(g.id_usuario, id_pedido)
    return jsonify({
        "mensaje": "Pedido marcado como LISTO",
        "id_pedido": id_pedido,
        "estado": estado_pedido(id_pedido),
    }), 200
