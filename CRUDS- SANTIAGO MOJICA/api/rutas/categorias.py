from flask import Blueprint, jsonify
from api.dao import categoria_dao
from api.errores import ErrorNegocio
from api.validaciones import obtener_json

bp = Blueprint("categorias", __name__, url_prefix="/api/v1")

@bp.get("/categorias")
def listar():
    return jsonify(categoria_dao.listar_categorias()), 200

@bp.get("/categorias/<int:id_categoria>")
def obtener(id_categoria):
    categoria = categoria_dao.obtener_categoria(id_categoria)
    if not categoria:
        raise ErrorNegocio(404, "CATEGORIA_NO_ENCONTRADA", "La categoría no existe")
    return jsonify(categoria), 200

@bp.post("/categorias")
def crear():
    datos = obtener_json()
    if "nombre" not in datos or not datos["nombre"].strip():
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "El nombre de la categoría es obligatorio")
    
    id_cat = categoria_dao.crear_categoria(datos["nombre"])
    return jsonify({"mensaje": "Categoría creada", "id_categoria": id_cat}), 201

@bp.put("/categorias/<int:id_categoria>")
def actualizar(id_categoria):
    datos = obtener_json()
    if "nombre" not in datos or not datos["nombre"].strip():
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "El nombre es obligatorio para actualizar")
        
    actualizado = categoria_dao.actualizar_categoria(id_categoria, datos["nombre"])
    if not actualizado:
        raise ErrorNegocio(404, "CATEGORIA_NO_ENCONTRADA", "La categoría no existe")
    return jsonify({"mensaje": "Categoría actualizada"}), 200

@bp.delete("/categorias/<int:id_categoria>")
def eliminar(id_categoria):
    eliminado = categoria_dao.eliminar_categoria(id_categoria)
    if not eliminado:
        raise ErrorNegocio(404, "CATEGORIA_NO_ENCONTRADA", "La categoría no existe")
    return jsonify({"mensaje": "Categoría eliminada"}), 200