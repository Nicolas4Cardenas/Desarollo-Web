"""Modelos ORM (SQLAlchemy 2.0) que reflejan las tablas de backend.sql."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ESTADOS_PEDIDO = ("PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO")


class Base(DeclarativeBase):
    pass


# Tabla intermedia pedido <-> mesa
pedido_mesa = Table(
    "pedido_mesa",
    Base.metadata,
    Column("id_pedido", Integer, ForeignKey("pedido.id_pedido"), primary_key=True),
    Column("id_mesa", Integer, ForeignKey("mesa.id_mesa"), primary_key=True),
)


class Rol(Base):
    __tablename__ = "rol"
    id_rol: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    usuario_login: Mapped[str] = mapped_column(String(50), unique=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"))
    rol: Mapped[Rol] = relationship(lazy="joined")


class Mesa(Base):
    __tablename__ = "mesa"
    id_mesa: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, unique=True)
    estado: Mapped[str] = mapped_column(String(20), default="libre")


class Categoria(Base):
    __tablename__ = "categoria"
    id_categoria: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)
    productos: Mapped[List[Producto]] = relationship(back_populates="categoria")


class Producto(Base):
    __tablename__ = "producto"
    id_producto: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    disponibilidad: Mapped[bool] = mapped_column(Boolean, default=True)
    id_categoria: Mapped[int] = mapped_column(ForeignKey("categoria.id_categoria"))
    categoria: Mapped[Categoria] = relationship(back_populates="productos", lazy="joined")


class Pedido(Base):
    __tablename__ = "pedido"
    id_pedido: Mapped[int] = mapped_column(primary_key=True)
    id_usuario_mesero: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime)
    fecha_ultima_actualizacion: Mapped[datetime] = mapped_column(DateTime)

    mesero: Mapped[Usuario] = relationship(lazy="joined")
    mesas: Mapped[List[Mesa]] = relationship(
        secondary=pedido_mesa, lazy="selectin", order_by="Mesa.numero"
    )
    detalles: Mapped[List[DetallePedido]] = relationship(
        back_populates="pedido", lazy="selectin", order_by="DetallePedido.id_detalle"
    )

    @property
    def total(self) -> Decimal:
        return sum((d.subtotal for d in self.detalles), Decimal("0"))

    @property
    def mesas_txt(self) -> str:
        return ",".join(str(m.numero) for m in self.mesas) or "-"


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"
    id_detalle: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"))
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"))
    cantidad: Mapped[int] = mapped_column(Integer)
    notas: Mapped[Optional[str]] = mapped_column(String(255))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    pedido: Mapped[Pedido] = relationship(back_populates="detalles")
    producto: Mapped[Producto] = relationship(lazy="joined")

    @property
    def subtotal(self) -> Decimal:
        return self.cantidad * self.precio_unitario


class HistorialEstado(Base):
    __tablename__ = "historial_estado"
    id_historial: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"))
    estado: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime)
    id_usuario_cambio: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
