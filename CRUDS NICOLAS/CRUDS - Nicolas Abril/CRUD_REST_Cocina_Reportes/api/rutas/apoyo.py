"""Rutas de APOYO (HU de Juan y Santiago que mi parte necesita para funcionar de punta a punta).

Sirven para armar la demo desde Postman sin usar Workbench:
  GET  /salud                          estado del servicio
  GET  /menu                  (mesero) menú disponible
  GET  /mesas/libres          (mesero) mesas libres
  POST /pedidos               (mesero) HU-01 crear pedido
  POST /pedidos/<id>/productos (mesero) HU-02 agregar producto
  PUT  /pedidos/<id>/entregar (mesero) HU-04 marcar entregado (necesario para los reportes)
  DELETE /pedidos/<id>        (mesero) HU-05 cancelar pedido (queda en el historial)
  GET  /pedidos[?estado=]     (admin)  listar TODOS los pedidos
  GET  /pedidos/<id>          (admin)  ver un pedido con sus productos
"""
from flask import Blueprint, g, jsonify, request, url_for

from api.auth import requiere_usuario
from api.dao import apoyo_dao
from api.errores import ErrorNegocio
from api.validaciones import ESTADOS_PEDIDO, entero_positivo, notas_opcionales, obtener_json

bp = Blueprint("apoyo", __name__, url_prefix="/api/v1")


def _pedido_o_404(id_pedido):
    pedido = apoyo_dao.obtener_pedido(g.id_usuario, id_pedido)
    if pedido is None:
        raise ErrorNegocio(404, "PEDIDO_NO_EXISTE", "El pedido indicado no existe")
    return pedido


@bp.get("/salud")
def salud():
    return jsonify({"servicio": "Polirestaurante REST - Nicolas (cocina, reportes, historial)",
                    "estado": "ok"}), 200


@bp.get("/menu")
@requiere_usuario
def menu():
    return jsonify(apoyo_dao.listar_menu(g.id_usuario)), 200


@bp.get("/mesas/libres")
@requiere_usuario
def mesas_libres():
    return jsonify(apoyo_dao.listar_mesas_libres(g.id_usuario)), 200


@bp.post("/pedidos")
@requiere_usuario
def crear_pedido():
    datos = obtener_json()
    id_mesa = entero_positivo(datos, "id_mesa")
    id_pedido = apoyo_dao.crear_pedido(g.id_usuario, id_mesa)
    respuesta = jsonify({"mensaje": "Pedido creado en estado PENDIENTE", "id_pedido": id_pedido})
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for("apoyo.obtener_pedido", id_pedido=id_pedido)
    return respuesta


@bp.post("/pedidos/<int:id_pedido>/productos")
@requiere_usuario
def agregar_producto(id_pedido):
    datos = obtener_json()
    id_producto = entero_positivo(datos, "id_producto")
    cantidad = entero_positivo(datos, "cantidad")
    resultado = apoyo_dao.agregar_producto(g.id_usuario, id_pedido, id_producto, cantidad,
                                           notas_opcionales(datos))
    return jsonify({"mensaje": "Producto agregado al pedido", **resultado}), 201


@bp.put("/pedidos/<int:id_pedido>/entregar")
@requiere_usuario
def marcar_entregado(id_pedido):
    apoyo_dao.marcar_entregado(g.id_usuario, id_pedido)
    return jsonify({"mensaje": "Pedido marcado como ENTREGADO", "id_pedido": id_pedido,
                    "estado": "ENTREGADO"}), 200


@bp.delete("/pedidos/<int:id_pedido>")
@requiere_usuario
def cancelar_pedido(id_pedido):
    apoyo_dao.cancelar_pedido(g.id_usuario, id_pedido)
    return jsonify({"mensaje": "Pedido CANCELADO (queda registrado en el historial)",
                    "id_pedido": id_pedido, "estado": "CANCELADO"}), 200


@bp.get("/pedidos")
@requiere_usuario
def listar_pedidos():
    estado = request.args.get("estado")
    if estado is not None:
        estado = estado.strip().upper()
        if estado not in ESTADOS_PEDIDO:
            raise ErrorNegocio(400, "ESTADO_INVALIDO",
                               "Estado inválido. Valores permitidos: " + ", ".join(sorted(ESTADOS_PEDIDO)))
    return jsonify(apoyo_dao.listar_pedidos(g.id_usuario, estado)), 200


@bp.get("/pedidos/<int:id_pedido>")
@requiere_usuario
def obtener_pedido(id_pedido):
    return jsonify(_pedido_o_404(id_pedido)), 200
