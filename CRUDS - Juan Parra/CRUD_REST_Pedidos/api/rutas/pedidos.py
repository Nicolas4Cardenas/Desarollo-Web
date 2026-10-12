"""Rutas REST del módulo MESERO (HU-01 a HU-05).

Recurso principal: /api/v1/pedidos      Sub-recurso: /pedidos/<id>/productos

  HU-01  POST   /pedidos                                  crear pedido
  HU-02  POST   /pedidos/<id>/productos                   agregar producto
  HU-03  PUT    /pedidos/<id>/productos/<id_detalle>      editar cantidad/notas
  HU-03  DELETE /pedidos/<id>/productos/<id_detalle>      quitar producto
  HU-04  PUT    /pedidos/<id>/entregar                    marcar como entregado
  HU-05  DELETE /pedidos/<id>                             cancelar pedido
  (R)    GET    /pedidos, /pedidos/<id>, /menu, /mesas/libres   consultas
"""
from flask import Blueprint, g, jsonify, request, url_for

from api.auth import requiere_usuario
from api.dao import pedido_dao
from api.errores import ErrorNegocio
from api.validaciones import ESTADOS_PEDIDO, entero_positivo, notas_opcionales, obtener_json

bp = Blueprint("pedidos", __name__, url_prefix="/api/v1")


def _pedido_o_404(id_pedido):
    pedido = pedido_dao.obtener_pedido(g.id_usuario, id_pedido)
    if pedido is None:
        raise ErrorNegocio(404, "PEDIDO_NO_EXISTE", "El pedido no existe o no pertenece a este mesero")
    return pedido


def _detalle_o_404(id_pedido, id_detalle):
    detalle = pedido_dao.obtener_detalle(g.id_usuario, id_pedido, id_detalle)
    if detalle is None:
        raise ErrorNegocio(404, "DETALLE_NO_EXISTE", "El producto indicado no hace parte de este pedido")
    return detalle


# ------------------------------------------------------------------ consultas
@bp.get("/salud")
def salud():
    return jsonify({"servicio": "Polirestaurante REST", "estado": "ok"}), 200


@bp.get("/menu")
@requiere_usuario
def menu():
    return jsonify(pedido_dao.listar_menu(g.id_usuario)), 200


@bp.get("/mesas/libres")
@requiere_usuario
def mesas_libres():
    return jsonify(pedido_dao.listar_mesas_libres(g.id_usuario)), 200


@bp.get("/pedidos")
@requiere_usuario
def listar_pedidos():
    estado = request.args.get("estado")
    if estado is not None:
        estado = estado.strip().upper()
        if estado not in ESTADOS_PEDIDO:
            raise ErrorNegocio(
                400, "ESTADO_INVALIDO",
                "Estado inválido. Valores permitidos: " + ", ".join(sorted(ESTADOS_PEDIDO)),
            )
    return jsonify(pedido_dao.listar_pedidos(g.id_usuario, estado)), 200


@bp.get("/pedidos/<int:id_pedido>")
@requiere_usuario
def obtener_pedido(id_pedido):
    return jsonify(_pedido_o_404(id_pedido)), 200


# ---------------------------------------------------------------- HU-01 crear
@bp.post("/pedidos")
@requiere_usuario
def crear_pedido():
    datos = obtener_json()
    id_mesa = entero_positivo(datos, "id_mesa")
    id_pedido = pedido_dao.crear_pedido(g.id_usuario, id_mesa)
    respuesta = jsonify({
        "mensaje": "Pedido creado en estado PENDIENTE",
        "pedido": _pedido_o_404(id_pedido),
    })
    respuesta.status_code = 201
    respuesta.headers["Location"] = url_for("pedidos.obtener_pedido", id_pedido=id_pedido)
    return respuesta


# ------------------------------------------------------ HU-02 agregar producto
@bp.post("/pedidos/<int:id_pedido>/productos")
@requiere_usuario
def agregar_producto(id_pedido):
    datos = obtener_json()
    id_producto = entero_positivo(datos, "id_producto")
    cantidad = entero_positivo(datos, "cantidad")
    _, notas = notas_opcionales(datos)
    resultado = pedido_dao.agregar_producto(g.id_usuario, id_pedido, id_producto, cantidad, notas)
    return jsonify({
        "mensaje": "Producto agregado al pedido (si ya estaba, se sumó la cantidad)",
        **resultado,
    }), 201


# ------------------------------------------------------ HU-03 editar / quitar
@bp.put("/pedidos/<int:id_pedido>/productos/<int:id_detalle>")
@requiere_usuario
def editar_producto(id_pedido, id_detalle):
    datos = obtener_json()
    cantidad = entero_positivo(datos, "cantidad")
    enviada, notas = notas_opcionales(datos)
    actual = _detalle_o_404(id_pedido, id_detalle)
    if not enviada:                       # si no mandan 'notas', se conservan las actuales
        notas = actual["notas"]
    resultado = pedido_dao.modificar_detalle(g.id_usuario, id_detalle, cantidad, notas)
    return jsonify({"mensaje": "Producto actualizado", **resultado}), 200


@bp.delete("/pedidos/<int:id_pedido>/productos/<int:id_detalle>")
@requiere_usuario
def quitar_producto(id_pedido, id_detalle):
    _detalle_o_404(id_pedido, id_detalle)
    resultado = pedido_dao.quitar_producto(g.id_usuario, id_detalle)
    return jsonify({"mensaje": "Producto quitado del pedido", **resultado}), 200


# ------------------------------------------------------ HU-04 marcar entregado
@bp.put("/pedidos/<int:id_pedido>/entregar")
@requiere_usuario
def marcar_entregado(id_pedido):
    pedido_dao.marcar_entregado(g.id_usuario, id_pedido)
    return jsonify({
        "mensaje": "Pedido marcado como ENTREGADO",
        "pedido": _pedido_o_404(id_pedido),
    }), 200


# ------------------------------------------------------------ HU-05 cancelar
@bp.delete("/pedidos/<int:id_pedido>")
@requiere_usuario
def cancelar_pedido(id_pedido):
    pedido_dao.cancelar_pedido(g.id_usuario, id_pedido)
    return jsonify({
        "mensaje": "Pedido CANCELADO (queda registrado en el historial)",
        "pedido": _pedido_o_404(id_pedido),
    }), 200
