"""Consultas de lectura con el ORM (SQLAlchemy)."""
from typing import Iterable, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import get_engine
from .models import Categoria, Mesa, Pedido, Producto, Rol, Usuario


def _sesion() -> Session:
    # Sesiones cortas: cada consulta ve datos frescos y los objetos quedan usables.
    return Session(get_engine(), expire_on_commit=False)


# ----------------------------------------------------------------- catálogo
def menu_disponible() -> List[Producto]:
    with _sesion() as s:
        stmt = (select(Producto).join(Producto.categoria)
                .where(Producto.disponibilidad.is_(True))
                .order_by(Categoria.nombre, Producto.nombre))
        return list(s.scalars(stmt))


def productos() -> List[Producto]:
    with _sesion() as s:
        stmt = select(Producto).join(Producto.categoria).order_by(Categoria.nombre, Producto.nombre)
        return list(s.scalars(stmt))


def producto(id_producto: int) -> Optional[Producto]:
    with _sesion() as s:
        return s.get(Producto, id_producto)


def categorias_con_conteo() -> list:
    with _sesion() as s:
        stmt = (select(Categoria.id_categoria, Categoria.nombre, func.count(Producto.id_producto))
                .outerjoin(Producto, Producto.id_categoria == Categoria.id_categoria)
                .group_by(Categoria.id_categoria, Categoria.nombre)
                .order_by(Categoria.nombre))
        return [tuple(r) for r in s.execute(stmt)]


def mesas(estado: Optional[str] = None) -> List[Mesa]:
    with _sesion() as s:
        stmt = select(Mesa).order_by(Mesa.numero)
        if estado:
            stmt = stmt.where(Mesa.estado == estado)
        return list(s.scalars(stmt))


def usuarios() -> List[Usuario]:
    with _sesion() as s:
        stmt = select(Usuario).join(Usuario.rol).order_by(Rol.nombre, Usuario.nombre)
        return list(s.scalars(stmt))


def roles() -> List[str]:
    with _sesion() as s:
        return list(s.scalars(select(Rol.nombre).order_by(Rol.id_rol)))


# ------------------------------------------------------------------ pedidos
def pedidos(id_mesero: Optional[int] = None, estados: Optional[Iterable[str]] = None) -> List[Pedido]:
    with _sesion() as s:
        stmt = select(Pedido).order_by(Pedido.fecha_creacion.desc(), Pedido.id_pedido.desc())
        if id_mesero is not None:
            stmt = stmt.where(Pedido.id_usuario_mesero == id_mesero)
        if estados:
            stmt = stmt.where(Pedido.estado.in_(list(estados)))
        return list(s.scalars(stmt))


def pedido(id_pedido: int) -> Optional[Pedido]:
    with _sesion() as s:
        return s.get(Pedido, id_pedido)


def cola_pendientes() -> List[Pedido]:
    """Pendientes con al menos un producto, el más antiguo primero (HU-06)."""
    with _sesion() as s:
        stmt = (select(Pedido)
                .where(Pedido.estado == "PENDIENTE", Pedido.detalles.any())
                .order_by(Pedido.fecha_creacion, Pedido.id_pedido))
        return list(s.scalars(stmt))


def en_preparacion() -> List[Pedido]:
    with _sesion() as s:
        stmt = (select(Pedido).where(Pedido.estado == "EN_PREPARACION")
                .order_by(Pedido.fecha_ultima_actualizacion, Pedido.id_pedido))
        return list(s.scalars(stmt))
