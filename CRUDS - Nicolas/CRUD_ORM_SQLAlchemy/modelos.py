from sqlalchemy.orm import DeclarativeBase,mapped_column,relationship
from sqlalchemy import Integer,String,ForeignKey,DateTime,Numeric,Boolean,Text
class Base(DeclarativeBase): pass
class Pedido(Base):
 __tablename__='pedido'
 id_pedido=mapped_column(Integer,primary_key=True)
 id_usuario_mesero=mapped_column(ForeignKey('usuario.id_usuario'))
 estado=mapped_column(String(20))
 fecha_creacion=mapped_column(DateTime)
 fecha_ultima_actualizacion=mapped_column(DateTime)
class Usuario(Base):
 __tablename__='usuario'
 id_usuario=mapped_column(Integer,primary_key=True)
 nombre=mapped_column(String(100));usuario_login=mapped_column(String(50));contrasena_hash=mapped_column(String(255));activo=mapped_column(Boolean);id_rol=mapped_column(ForeignKey('rol.id_rol'))
class Rol(Base):
 __tablename__='rol'
 id_rol=mapped_column(Integer,primary_key=True);nombre=mapped_column(String(30))
class HistorialEstado(Base):
 __tablename__='historial_estado'
 id_historial=mapped_column(Integer,primary_key=True)
 id_pedido=mapped_column(ForeignKey('pedido.id_pedido'))
 estado=mapped_column(String(20));fecha=mapped_column(DateTime);id_usuario_cambio=mapped_column(ForeignKey('usuario.id_usuario'))
class ReporteGuardado(Base):
 __tablename__='nicolas_reporte_guardado'
 id_reporte=mapped_column(Integer,primary_key=True)
 tipo=mapped_column(String(20));nombre=mapped_column(String(100));fecha_inicio=mapped_column(DateTime);fecha_fin=mapped_column(DateTime);filtro_categoria=mapped_column(Integer);filtro_producto=mapped_column(Integer);creado_por=mapped_column(ForeignKey('usuario.id_usuario'));creado_en=mapped_column(DateTime)
