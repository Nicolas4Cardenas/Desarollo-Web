from flask import Blueprint, jsonify
from flask_bcrypt import Bcrypt
from api.dao import auth_dao
from api.errores import ErrorNegocio
from api.validaciones import obtener_json

bp = Blueprint("auth", __name__, url_prefix="/api/v1")
bcrypt = Bcrypt()

@bp.post("/login")
def login():
    datos = obtener_json()
    
    if not all(k in datos for k in ("usuario_login", "contrasena")):
        raise ErrorNegocio(400, "DATOS_INVALIDOS", "Se requiere usuario_login y contrasena")
    
    usuario_login = datos["usuario_login"]
    contrasena_ingresada = datos["contrasena"]
    
    
    usuario = auth_dao.obtener_usuario_por_login(usuario_login)
    
    if not usuario:
        raise ErrorNegocio(401, "CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos")
    
    
    hash_almacenado = usuario["contrasena_hash"]
    
    
    if not bcrypt.check_password_hash(hash_almacenado, contrasena_ingresada):
        raise ErrorNegocio(401, "CREDENCIALES_INVALIDAS", "Usuario o contraseña incorrectos")
    
    
    return jsonify({
        "mensaje": "Login exitoso",
        "id_usuario": usuario["id_usuario"],
        "nombre": usuario["nombre"],
        "rol": usuario["rol"]
    }), 200