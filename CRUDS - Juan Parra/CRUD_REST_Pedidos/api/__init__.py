"""Fábrica de la aplicación Flask (Polirestaurante - servicio REST del módulo mesero)."""
from datetime import date, datetime
from decimal import Decimal

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from api.errores import registrar_manejadores
from api.rutas.pedidos import bp as pedidos_bp


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
    ensure_ascii = False          # tildes y ñ legibles en Postman
    sort_keys = False             # respeta el orden de los campos


def crear_app():
    app = Flask(__name__)
    app.json = ProveedorJSON(app)
    app.register_blueprint(pedidos_bp)
    registrar_manejadores(app)
    return app
