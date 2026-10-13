from flask import Blueprint, jsonify
from api.dao import producto_dao
from api.errores import ErrorNegocio
from api.validaciones import obtener_json

bp = Blueprint("productos", __name__, url_prefix="/api/v1")

@bp.get("/productos")
def listar():
    return jsonify(producto_dao.listar_productos()), 200

@bp.get("/productos/<int:id_producto>")
def obtener(id_producto):
    producto = producto_dao.obtener_producto(id_producto)
    if not producto:
        raise ErrorNegocio(404, "PRODUCTO_NO_ENCONTRADO", "El producto no existe")
    return jsonify(producto), 200

@bp.post("/productos")
def crear():
    datos = obtener_json()
    if not all(k in datos for k in ("nombre", "precio", "id_categoria")):
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "Nombre, precio y categoría son obligatorios")
    
    id_prod = producto_dao.crear_producto(
        datos["nombre"], 
        datos.get("descripcion", ""), 
        datos["precio"], 
        datos.get("disponibilidad", True), 
        datos["id_categoria"]
    )
    return jsonify({"mensaje": "Producto creado", "id_producto": id_prod}), 201

@bp.put("/productos/<int:id_producto>")
def actualizar(id_producto):
    datos = obtener_json()
    if not all(k in datos for k in ("nombre", "precio", "id_categoria")):
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "Nombre, precio y categoría son obligatorios")
        
    actualizado = producto_dao.actualizar_producto(
        id_producto, 
        datos["nombre"], 
        datos.get("descripcion", ""), 
        datos["precio"], 
        datos.get("disponibilidad", True), 
        datos["id_categoria"]
    )
    if not actualizado:
        raise ErrorNegocio(404, "PRODUCTO_NO_ENCONTRADO", "El producto no existe")
    return jsonify({"mensaje": "Producto actualizado"}), 200

@bp.delete("/productos/<int:id_producto>")
def eliminar(id_producto):
    eliminado = producto_dao.eliminar_producto(id_producto)
    if not eliminado:
        raise ErrorNegocio(404, "PRODUCTO_NO_ENCONTRADO", "El producto no existe")
    return jsonify({"mensaje": "Producto eliminado"}), 200