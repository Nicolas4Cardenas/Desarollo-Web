"""Modelos del ORM: una clase por tabla de backend.sql (mismos nombres de tabla y columna)."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Table, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Tabla intermedia pedido <-> mesa (solo tiene las dos llaves, por eso es un Table
# y no una clase)
pedido_mesa = Table(
    "pedido_mesa",
    Base.metadata,
    Column("id_pedido", ForeignKey("pedido.id_pedido"), primary_key=True),
    Column("id_mesa", ForeignKey("mesa.id_mesa"), primary_key=True),
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

    rol: Mapped[Rol] = relationship()


class Mesa(Base):
    __tablename__ = "mesa"

    id_mesa: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True)
    estado: Mapped[str] = mapped_column(String(20), default="libre")


class Categoria(Base):
    __tablename__ = "categoria"

    id_categoria: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)


class Producto(Base):
    __tablename__ = "producto"

    id_producto: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    disponibilidad: Mapped[bool] = mapped_column(Boolean, default=True)
    id_categoria: Mapped[int] = mapped_column(ForeignKey("categoria.id_categoria"))

    categoria: Mapped[Categoria] = relationship()


class Pedido(Base):
    __tablename__ = "pedido"

    id_pedido: Mapped[int] = mapped_column(primary_key=True)
    id_usuario_mesero: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_ultima_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    mesero: Mapped[Usuario] = relationship()
    mesas: Mapped[List[Mesa]] = relationship(secondary=pedido_mesa)
    detalles: Mapped[List["DetallePedido"]] = relationship(
        back_populates="pedido", order_by="DetallePedido.id_detalle"
    )


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"

    id_detalle: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"))
    id_producto: Mapped[int] = mapped_column(ForeignKey("producto.id_producto"))
    cantidad: Mapped[int]
    notas: Mapped[Optional[str]] = mapped_column(String(255))
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    pedido: Mapped[Pedido] = relationship(back_populates="detalles")
    producto: Mapped[Producto] = relationship()


class HistorialEstado(Base):
    __tablename__ = "historial_estado"

    id_historial: Mapped[int] = mapped_column(primary_key=True)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedido.id_pedido"))
    estado: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    id_usuario_cambio: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
