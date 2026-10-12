"""Manejo de errores: traduce los errores de la base de datos a respuestas HTTP.

Los procedimientos del backend.sql lanzan errores con el formato
    'CODIGO: mensaje legible'   (SQLSTATE 45000, errno 1644)
Aquí se convierte ese CODIGO en el código de estado HTTP adecuado.
"""
import logging

import pymysql
from flask import jsonify

log = logging.getLogger(__name__)

# Código de negocio (viene del backend.sql) -> código HTTP
HTTP_POR_CODIGO = {
    "ACCESO_DENEGADO": 403,
    "PEDIDO_NO_EXISTE": 404,
    "MESA_NO_EXISTE": 404,
    "PRODUCTO_NO_EXISTE": 404,
    "DETALLE_NO_EXISTE": 404,
    "CANTIDAD_INVALIDA": 400,
    "MESA_OCUPADA": 409,
    "PEDIDO_BLOQUEADO": 409,
    "PRODUCTO_NO_DISPONIBLE": 409,
    "TRANSICION_INVALIDA": 409,
    "CANCELACION_NO_PERMITIDA": 409,
}

ERRNO_SIGNAL = 1644                              # SIGNAL SQLSTATE '45000'
ERRNO_SIN_CONEXION = {1045, 1049, 2002, 2003, 2006, 2013}


class ErrorNegocio(Exception):
    """Error controlado de la API (validaciones, recurso no encontrado, etc.)."""

    def __init__(self, status, codigo, mensaje):
        super().__init__(mensaje)
        self.status = status
        self.codigo = codigo
        self.mensaje = mensaje


def _respuesta(status, codigo, mensaje):
    return jsonify({"error": mensaje, "codigo": codigo}), status


def registrar_manejadores(app):
    @app.errorhandler(ErrorNegocio)
    def _negocio(e):
        return _respuesta(e.status, e.codigo, e.mensaje)

    @app.errorhandler(pymysql.MySQLError)
    def _mysql(e):
        errno = e.args[0] if e.args else None
        texto = str(e.args[1]) if len(e.args) > 1 else str(e)

        if errno == ERRNO_SIGNAL:
            codigo, _, mensaje = texto.partition(":")
            codigo = codigo.strip()
            return _respuesta(HTTP_POR_CODIGO.get(codigo, 400), codigo, mensaje.strip() or texto)

        if errno in ERRNO_SIN_CONEXION:
            log.error("Sin conexión a la base de datos: %s", e)
            return _respuesta(503, "BD_NO_DISPONIBLE", "No se pudo conectar con la base de datos")

        log.exception("Error de base de datos no controlado")
        return _respuesta(500, "ERROR_BD", "Error interno de base de datos")

    @app.errorhandler(404)
    def _no_encontrado(_):
        return _respuesta(404, "RUTA_NO_ENCONTRADA", "Recurso no encontrado")

    @app.errorhandler(405)
    def _metodo(_):
        return _respuesta(405, "METODO_NO_PERMITIDO", "Método HTTP no permitido para esta ruta")

    @app.errorhandler(500)
    def _servidor(e):
        log.exception("Error interno: %s", e)
        return _respuesta(500, "ERROR_INTERNO", "Error interno del servidor")
