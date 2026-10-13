"""Fábrica de la aplicación Flask (Polirestaurante - servicio REST de administración)."""
from datetime import date, datetime
from decimal import Decimal

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from api.errores import registrar_manejadores
from api.rutas.categorias import bp as categorias_bp
from api.rutas.productos import bp as productos_bp
from api.rutas.mesas import bp as mesas_bp
from api.rutas.usuarios import bp as usuarios_bp
from api.rutas.auth import bp as auth_bp  


def _serializar(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, datetime):
        return o.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(o, date):
        return o.isoformat()
    raise TypeError(f"{type(o)} no es serializable a JSON")


class ProveedorJSON(DefaultJSONProvider):
    default = staticmethod(_serializar)
    ensure_ascii = False          
    sort_keys = False             


def crear_app():
    app = Flask(__name__)
    app.json = ProveedorJSON(app)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(productos_bp)
    app.register_blueprint(mesas_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(auth_bp)  
    registrar_manejadores(app)
    return app