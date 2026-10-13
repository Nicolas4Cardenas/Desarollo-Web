"""Modelos ORM (SQLAlchemy). Cada clase mapea una tabla ya creada por backend.sql.

Tabla = Clase | Columna = Atributo | Clave foránea = relationship()
(No se usa create_all(): el esquema, los triggers y los datos semilla vienen del backend.sql.)
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Table, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Tabla intermedia de la relación muchos a muchos pedido <-> mesa
pedido_mesa = Table(
    "pedido_mesa", Base.metadata,
    Column("id_pedido", Integer, ForeignKey("pedido.id_pedido"), primary_key=True),
    Column("id_mesa", Integer, ForeignKey("mesa.id_mesa"), primary_key=True),
)


class Rol(Base):
    __tablename__ = "rol"
    id_rol = Column(Integer, primary_key=True)
    nombre = Column(String(30), nullable=False, unique=True)


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    usuario_login = Column(String(50), nullable=False, unique=True)
    contrasena_hash = Column(String(255), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), nullable=False)
    rol = relationship("Rol")


class Mesa(Base):
    __tablename__ = "mesa"
    id_mesa = Column(Integer, primary_key=True)
    numero = Column(Integer, nullable=False, unique=True)
    estado = Column(String(20), nullable=False, default="libre")
    pedidos = relationship("Pedido", secondary=pedido_mesa, back_populates="mesas")


class Categoria(Base):
    __tablename__ = "categoria"
    id_categoria = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False, unique=True)


class Producto(Base):
    __tablename__ = "producto"
    id_producto = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255))
    precio = Column(Numeric(10, 2), nullable=False)
    disponibilidad = Column(Boolean, nullable=False, default=True)
    id_categoria = Column(Integer, ForeignKey("categoria.id_categoria"), nullable=False)
    categoria = relationship("Categoria")


class Pedido(Base):
    __tablename__ = "pedido"
    id_pedido = Column(Integer, primary_key=True)
    id_usuario_mesero = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    estado = Column(String(20), nullable=False, default="PENDIENTE")
    fecha_creacion = Column(DateTime, nullable=False, default=func.now())
    fecha_ultima_actualizacion = Column(DateTime, nullable=False, default=func.now())

    mesero = relationship("Usuario")
    mesas = relationship("Mesa", secondary=pedido_mesa, back_populates="pedidos")
    # 1:N con borrado en cascada de renglones huérfanos (permite pedido.detalles.remove(d))
    detalles = relationship("DetallePedido", back_populates="pedido",
                            cascade="all, delete-orphan", order_by="DetallePedido.id_detalle")
    # El historial es inmutable: se guarda con el pedido pero nunca se borra desde el ORM
    historial = relationship("HistorialEstado", back_populates="pedido",
                             cascade="save-update, merge", order_by="HistorialEstado.id_historial")

    @property
    def total(self):
        return sum((d.cantidad * d.precio_unitario for d in self.detalles), 0)


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"
    id_detalle = Column(Integer, primary_key=True)
    id_pedido = Column(Integer, ForeignKey("pedido.id_pedido"), nullable=False)
    id_producto = Column(Integer, ForeignKey("producto.id_producto"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    notas = Column(String(255))
    precio_unitario = Column(Numeric(10, 2), nullable=False)

    pedido = relationship("Pedido", back_populates="detalles")
    producto = relationship("Producto")


class HistorialEstado(Base):
    __tablename__ = "historial_estado"
    id_historial = Column(Integer, primary_key=True)
    id_pedido = Column(Integer, ForeignKey("pedido.id_pedido"), nullable=False)
    estado = Column(String(20), nullable=False)
    fecha = Column(DateTime, nullable=False, default=func.now())
    id_usuario_cambio = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)

    pedido = relationship("Pedido", back_populates="historial")
    usuario = relationship("Usuario")
