"""Rutas REST de REPORTES (HU-13 ventas, HU-14 tiempos). Requiere usuario ADMINISTRADOR.

  HU-13  GET /reportes/ventas?desde=AAAA-MM-DD&hasta=AAAA-MM-DD[&id_categoria=][&id_producto=]
  HU-14  GET /reportes/tiempos?desde=AAAA-MM-DD&hasta=AAAA-MM-DD
"""
from flask import Blueprint, g, jsonify

from api.auth import requiere_usuario
from api.dao import reportes_dao
from api.validaciones import entero_de_query, fecha_de_query

bp = Blueprint("reportes", __name__, url_prefix="/api/v1/reportes")


@bp.get("/ventas")
@requiere_usuario
def reporte_ventas():
    desde, hasta = fecha_de_query("desde"), fecha_de_query("hasta")
    reporte = reportes_dao.reporte_ventas(
        g.id_usuario, desde, hasta, entero_de_query("id_categoria"), entero_de_query("id_producto"))
    return jsonify({"desde": desde, "hasta": hasta, **reporte}), 200


@bp.get("/tiempos")
@requiere_usuario
def reporte_tiempos():
    desde, hasta = fecha_de_query("desde"), fecha_de_query("hasta")
    reporte = reportes_dao.reporte_tiempos(g.id_usuario, desde, hasta)
    return jsonify({"desde": desde, "hasta": hasta, **reporte}), 200
