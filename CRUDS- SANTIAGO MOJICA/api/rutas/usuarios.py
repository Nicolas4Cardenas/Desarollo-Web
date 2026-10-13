from flask import Blueprint, jsonify
from api.dao import usuario_dao
from api.errores import ErrorNegocio
from api.validaciones import obtener_json

bp = Blueprint("usuarios", __name__, url_prefix="/api/v1")

@bp.get("/usuarios")
def listar():
    return jsonify(usuario_dao.listar_usuarios()), 200

@bp.get("/usuarios/<int:id_usuario>")
def obtener(id_usuario):
    usuario = usuario_dao.obtener_usuario(id_usuario)
    if not usuario:
        raise ErrorNegocio(404, "USUARIO_NO_ENCONTRADO", "El usuario no existe")
    return jsonify(usuario), 200

@bp.post("/usuarios")
def crear():
    datos = obtener_json()
    if not all(k in datos for k in ("nombre", "usuario_login", "contrasena", "id_rol")):
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "Faltan datos obligatorios")
    
    # OJO: Aquí deberíamos encriptar la contraseña (bcrypt), por ahora la guardamos como llega
    # para que no te estanques, y en el Login lo ajustamos.
    id_usr = usuario_dao.crear_usuario(datos["nombre"], datos["usuario_login"], datos["contrasena"], datos["id_rol"])
    return jsonify({"mensaje": "Usuario creado", "id_usuario": id_usr}), 201

@bp.put("/usuarios/<int:id_usuario>")
def actualizar(id_usuario):
    datos = obtener_json()
    if not all(k in datos for k in ("nombre", "usuario_login", "id_rol")):
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "Faltan datos para actualizar")
        
    actualizado = usuario_dao.actualizar_usuario(id_usuario, datos["nombre"], datos["usuario_login"], datos["id_rol"])
    if not actualizado:
        raise ErrorNegocio(404, "USUARIO_NO_ENCONTRADO", "El usuario no existe")
    return jsonify({"mensaje": "Usuario actualizado"}), 200

@bp.delete("/usuarios/<int:id_usuario>")
def eliminar(id_usuario):
    eliminado = usuario_dao.eliminar_usuario(id_usuario)
    if not eliminado:
        raise ErrorNegocio(404, "USUARIO_NO_ENCONTRADO", "El usuario no existe")
    return jsonify({"mensaje": "Usuario desactivado"}), 200