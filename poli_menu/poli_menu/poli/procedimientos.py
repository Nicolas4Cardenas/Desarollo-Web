"""Operaciones de negocio: llaman a los procedimientos almacenados vía PyMySQL.

La base valida rol, dueño del pedido, estados, etc. (RNF-06): aquí solo
se traducen los argumentos y los resultados.
"""
from decimal import Decimal
from typing import List, Optional

from .db import llamar, llamar_con_salida


def _filas(rs: List[list], i: int = 0) -> list:
    return rs[i] if len(rs) > i else []


# ------------------------------------------------------------------- auth
def obtener_credenciales(login: str) -> list:
    return _filas(llamar("sp_auth_obtener_credenciales", login))


# ----------------------------------------------------------------- mesero
def crear_pedido(id_usuario: int, id_mesa: int) -> int:
    return int(llamar_con_salida("sp_mesero_crear_pedido", id_usuario, id_mesa))


def agregar_producto(id_usuario, id_pedido, id_producto, cantidad, notas) -> Decimal:
    rs = llamar("sp_mesero_agregar_producto", id_usuario, id_pedido, id_producto, cantidad, notas)
    return _filas(rs)[0]["total"]


def modificar_detalle(id_usuario, id_detalle, cantidad, notas) -> Decimal:
    rs = llamar("sp_mesero_modificar_detalle", id_usuario, id_detalle, cantidad, notas)
    return _filas(rs)[0]["total"]


def quitar_producto(id_usuario, id_detalle) -> Decimal:
    rs = llamar("sp_mesero_quitar_producto", id_usuario, id_detalle)
    return _filas(rs)[0]["total"]


def marcar_entregado(id_usuario, id_pedido) -> None:
    llamar("sp_mesero_marcar_entregado", id_usuario, id_pedido)


def cancelar_pedido(id_usuario, id_pedido) -> None:
    llamar("sp_mesero_cancelar_pedido", id_usuario, id_pedido)


# ----------------------------------------------------------------- cocina
def iniciar_preparacion(id_usuario, id_pedido) -> None:
    llamar("sp_cocina_iniciar_preparacion", id_usuario, id_pedido)


def marcar_listo(id_usuario, id_pedido) -> None:
    llamar("sp_cocina_marcar_listo", id_usuario, id_pedido)


# ------------------------------------------------------------------ admin
def crear_categoria(uid, nombre) -> int:
    return _filas(llamar("sp_admin_crear_categoria", uid, nombre))[0]["id_categoria"]


def editar_categoria(uid, id_categoria, nombre) -> None:
    llamar("sp_admin_editar_categoria", uid, id_categoria, nombre)


def eliminar_categoria(uid, id_categoria) -> None:
    llamar("sp_admin_eliminar_categoria", uid, id_categoria)


def crear_producto(uid, nombre, descripcion, precio, id_categoria, disponible) -> int:
    rs = llamar("sp_admin_crear_producto", uid, nombre, descripcion, precio, id_categoria, disponible)
    return _filas(rs)[0]["id_producto"]


def editar_producto(uid, id_producto, nombre, descripcion, precio, id_categoria, disponible) -> None:
    llamar("sp_admin_editar_producto", uid, id_producto, nombre, descripcion, precio, id_categoria, disponible)


def activar_producto(uid, id_producto, disponible) -> None:
    llamar("sp_admin_activar_producto", uid, id_producto, disponible)


def eliminar_producto(uid, id_producto) -> None:
    llamar("sp_admin_eliminar_producto", uid, id_producto)


def crear_mesa(uid, numero) -> int:
    return _filas(llamar("sp_admin_crear_mesa", uid, numero))[0]["id_mesa"]


def editar_mesa(uid, id_mesa, numero) -> None:
    llamar("sp_admin_editar_mesa", uid, id_mesa, numero)


def cambiar_estado_mesa(uid, id_mesa, estado) -> None:
    llamar("sp_admin_cambiar_estado_mesa", uid, id_mesa, estado)


def crear_usuario(uid, nombre, login, hash_bcrypt, rol) -> int:
    return _filas(llamar("sp_admin_crear_usuario", uid, nombre, login, hash_bcrypt, rol))[0]["id_usuario"]


def editar_usuario(uid, id_usuario, nombre, rol) -> None:
    llamar("sp_admin_editar_usuario", uid, id_usuario, nombre, rol)


def cambiar_contrasena(uid, id_usuario, hash_bcrypt) -> None:
    llamar("sp_admin_cambiar_contrasena", uid, id_usuario, hash_bcrypt)


def activar_usuario(uid, id_usuario, activo) -> None:
    llamar("sp_admin_activar_usuario", uid, id_usuario, activo)


def reporte_ventas(uid, fecha_ini, fecha_fin, id_categoria: Optional[int], id_producto: Optional[int]):
    """Devuelve [totales, por_categoria, por_producto]."""
    return llamar("sp_admin_reporte_ventas", uid, fecha_ini, fecha_fin, id_categoria, id_producto)


def reporte_tiempos(uid, fecha_ini, fecha_fin):
    """Devuelve [detalle_por_pedido, promedios]."""
    return llamar("sp_admin_reporte_tiempos", uid, fecha_ini, fecha_fin)


def historial_pedido(uid, id_pedido) -> list:
    return _filas(llamar("sp_admin_ver_historial_pedido", uid, id_pedido))
