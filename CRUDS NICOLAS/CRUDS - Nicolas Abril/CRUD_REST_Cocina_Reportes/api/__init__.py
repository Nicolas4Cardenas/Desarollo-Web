"""Fábrica de la aplicación Flask (Polirestaurante - servicio REST de cocina, reportes e historial)."""
from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import Flask
from flask.json.provider import DefaultJSONProvider

from api.errores import registrar_manejadores
from api.rutas.apoyo import bp as apoyo_bp
from api.rutas.cocina import bp as cocina_bp
from api.rutas.historial import bp as historial_bp
from api.rutas.reportes import bp as reportes_bp


def _serializar(o):
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, datetime):
        return o.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, timedelta):
        return str(o)
    raise TypeError(f"{type(o)} no es serializable a JSON")


class ProveedorJSON(DefaultJSONProvider):
    default = staticmethod(_serializar)
    ensure_ascii = False          # tildes y ñ legibles en Postman
    sort_keys = False             # respeta el orden de los campos


def crear_app():
    app = Flask(__name__)
    app.json = ProveedorJSON(app)
    for bp in (apoyo_bp, cocina_bp, reportes_bp, historial_bp):
        app.register_blueprint(bp)
    registrar_manejadores(app)
    return app
