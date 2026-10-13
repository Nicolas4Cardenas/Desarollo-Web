from flask import Blueprint, jsonify
from api.dao import mesa_dao
from api.errores import ErrorNegocio
from api.validaciones import obtener_json

bp = Blueprint("mesas", __name__, url_prefix="/api/v1")

@bp.get("/mesas")
def listar():
    return jsonify(mesa_dao.listar_mesas()), 200

@bp.get("/mesas/<int:id_mesa>")
def obtener(id_mesa):
    mesa = mesa_dao.obtener_mesa(id_mesa)
    if not mesa:
        raise ErrorNegocio(404, "MESA_NO_ENCONTRADA", "La mesa no existe")
    return jsonify(mesa), 200

@bp.post("/mesas")
def crear():
    datos = obtener_json()
    if "numero" not in datos:
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "El número de mesa es obligatorio")
    
    id_mesa = mesa_dao.crear_mesa(datos["numero"])
    return jsonify({"mensaje": "Mesa creada", "id_mesa": id_mesa}), 201

@bp.put("/mesas/<int:id_mesa>")
def actualizar(id_mesa):
    datos = obtener_json()
    if "numero" not in datos or "estado" not in datos:
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "El número y estado son obligatorios")
        
    actualizado = mesa_dao.actualizar_mesa(id_mesa, datos["numero"], datos["estado"])
    if not actualizado:
        raise ErrorNegocio(404, "MESA_NO_ENCONTRADA", "La mesa no existe")
    return jsonify({"mensaje": "Mesa actualizada"}), 200

@bp.delete("/mesas/<int:id_mesa>")
def eliminar(id_mesa):
    eliminado = mesa_dao.eliminar_mesa(id_mesa)
    if not eliminado:
        raise ErrorNegocio(404, "MESA_NO_ENCONTRADA", "La mesa no existe")
    return jsonify({"mensaje": "Mesa eliminada"}), 200