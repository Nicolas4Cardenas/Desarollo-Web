"""CRUD de pedidos con ORM (SQLAlchemy). No hay SQL escrito a mano: se trabaja con
objetos (Pedido, DetallePedido, Mesa...) y la sesión genera los INSERT/UPDATE/DELETE.

Mismas reglas de negocio que la versión con driver (HU-01 a HU-05):
  session.add() = CREATE | session.query()/get() = READ | atributo modificado = UPDATE |
  session.delete() / lista.remove() = DELETE | commit/rollback en db.sesion()
"""
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from db import sesion
from errores import ErrorNegocio, SIN_CAMBIO
from modelos import DetallePedido, HistorialEstado, Mesa, Pedido, Producto, Usuario
from validaciones import limpiar_notas, validar_cantidad

TECNOLOGIA = "ORM SQLAlchemy"
ACTIVOS = ("PENDIENTE", "EN_PREPARACION", "LISTO")


# ------------------------------------------------------- reglas / auxiliares
def _exigir_rol(s, id_usuario, rol):
    usuario = s.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo or usuario.rol.nombre != rol:
        raise ErrorNegocio("ACCESO_DENEGADO", "El usuario no tiene permiso para esta operación")


def _pedido_propio(s, id_usuario, id_pedido):
    """Pedido bloqueado (FOR UPDATE) que debe existir y pertenecer al mesero."""
    pedido = s.query(Pedido).filter(Pedido.id_pedido == id_pedido).with_for_update().first()
    if pedido is None:
        raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
    if pedido.id_usuario_mesero != id_usuario:
        raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
    return pedido


def _exigir_pendiente(pedido):
    if pedido.estado != "PENDIENTE":
        raise ErrorNegocio("PEDIDO_BLOQUEADO", "Solo se puede editar un pedido en estado PENDIENTE")


def _liberar_mesas(s, pedido):
    """La mesa vuelve a 'libre' si no tiene otro pedido activo (HU-11)."""
    for mesa in pedido.mesas:
        otros = (s.query(Pedido).join(Pedido.mesas)
                 .filter(Mesa.id_mesa == mesa.id_mesa,
                         Pedido.id_pedido != pedido.id_pedido,
                         Pedido.estado.in_(ACTIVOS))
                 .count())
        if otros == 0:
            mesa.estado = "libre"


def _cambiar_estado(s, pedido, nuevo, id_usuario):
    pedido.estado = nuevo
    pedido.fecha_ultima_actualizacion = func.now()
    pedido.historial.append(HistorialEstado(estado=nuevo, fecha=func.now(), id_usuario_cambio=id_usuario))
    s.flush()
    if nuevo in ("ENTREGADO", "CANCELADO"):
        _liberar_mesas(s, pedido)


def _resumen(p):
    return {
        "id_pedido": p.id_pedido, "estado": p.estado,
        "fecha_creacion": p.fecha_creacion, "fecha_ultima_actualizacion": p.fecha_ultima_actualizacion,
        "mesero": p.mesero.nombre,
        "mesas": sorted(m.numero for m in p.mesas),
        "total": p.total,
    }


# ------------------------------------------------------------ usuarios y menú
def buscar_usuario(login):
    with sesion() as s:
        u = s.query(Usuario).filter(Usuario.usuario_login == login, Usuario.activo.is_(True)).first()
        return None if u is None else {"id_usuario": u.id_usuario, "nombre": u.nombre, "rol": u.rol.nombre}


def listar_menu(id_usuario):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        productos = s.query(Producto).filter(Producto.disponibilidad.is_(True)).all()
        productos.sort(key=lambda p: (p.categoria.nombre, p.nombre))
        return [{"categoria": p.categoria.nombre, "id_producto": p.id_producto, "nombre": p.nombre,
                 "descripcion": p.descripcion, "precio": p.precio} for p in productos]


def listar_mesas_libres(id_usuario):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        mesas = s.query(Mesa).filter(Mesa.estado == "libre").order_by(Mesa.numero).all()
        return [{"id_mesa": m.id_mesa, "numero": m.numero} for m in mesas]


# --------------------------------------------------------------- HU-01 CREATE
def crear_pedido(id_usuario, id_mesa):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        mesa = s.query(Mesa).filter(Mesa.id_mesa == id_mesa).with_for_update().first()
        if mesa is None:
            raise ErrorNegocio("MESA_NO_EXISTE", "La mesa indicada no existe")
        if mesa.estado != "libre":
            raise ErrorNegocio("MESA_OCUPADA", "La mesa no está disponible")
        pedido = Pedido(id_usuario_mesero=id_usuario, estado="PENDIENTE",
                        fecha_creacion=func.now(), fecha_ultima_actualizacion=func.now())
        pedido.mesas.append(mesa)                 # inserta en pedido_mesa automáticamente
        mesa.estado = "ocupada"
        pedido.historial.append(HistorialEstado(estado="PENDIENTE", fecha=func.now(),
                                                id_usuario_cambio=id_usuario))
        s.add(pedido)
        s.flush()                                  # genera el id_pedido
        return pedido.id_pedido


# ------------------------------------------------------------ HU-02 CREATE
def agregar_producto(id_usuario, id_pedido, id_producto, cantidad, notas=None):
    notas = limpiar_notas(notas)
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        validar_cantidad(cantidad)
        pedido = _pedido_propio(s, id_usuario, id_pedido)
        _exigir_pendiente(pedido)
        producto = s.get(Producto, id_producto)
        if producto is None:
            raise ErrorNegocio("PRODUCTO_NO_EXISTE", "El producto indicado no existe")
        if not producto.disponibilidad:
            raise ErrorNegocio("PRODUCTO_NO_DISPONIBLE", "El producto no está disponible")

        detalle = next((d for d in pedido.detalles if d.id_producto == id_producto), None)
        if detalle:          # un renglón por producto: se suma la cantidad
            detalle.cantidad += cantidad
            if notas:
                detalle.notas = notas
        else:
            detalle = DetallePedido(id_producto=id_producto, cantidad=cantidad, notas=notas,
                                    precio_unitario=producto.precio)
            pedido.detalles.append(detalle)
        pedido.fecha_ultima_actualizacion = func.now()
        s.flush()
        return {"id_detalle": detalle.id_detalle, "total": pedido.total}


# ------------------------------------------------------ HU-03 UPDATE / DELETE
def _detalle_del_pedido(s, pedido, id_detalle):
    detalle = next((d for d in pedido.detalles if d.id_detalle == id_detalle), None)
    if detalle is None:
        raise ErrorNegocio("DETALLE_NO_EXISTE", "El producto indicado no hace parte de este pedido")
    return detalle


def modificar_detalle(id_usuario, id_pedido, id_detalle, cantidad, notas=SIN_CAMBIO):
    if notas is not SIN_CAMBIO:
        notas = limpiar_notas(notas)
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        validar_cantidad(cantidad)
        pedido = _pedido_propio(s, id_usuario, id_pedido)
        detalle = _detalle_del_pedido(s, pedido, id_detalle)
        _exigir_pendiente(pedido)
        detalle.cantidad = cantidad
        if notas is not SIN_CAMBIO:
            detalle.notas = notas
        pedido.fecha_ultima_actualizacion = func.now()
        s.flush()
        return {"id_pedido": id_pedido, "total": pedido.total}


def quitar_producto(id_usuario, id_pedido, id_detalle):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        pedido = _pedido_propio(s, id_usuario, id_pedido)
        detalle = _detalle_del_pedido(s, pedido, id_detalle)
        _exigir_pendiente(pedido)
        pedido.detalles.remove(detalle)            # delete-orphan => DELETE en la BD
        pedido.fecha_ultima_actualizacion = func.now()
        s.flush()
        return {"id_pedido": id_pedido, "total": pedido.total}


# ------------------------------------------------------ HU-04 / HU-05 UPDATE
def marcar_entregado(id_usuario, id_pedido):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        pedido = _pedido_propio(s, id_usuario, id_pedido)
        if pedido.estado != "LISTO":
            raise ErrorNegocio("TRANSICION_INVALIDA", "Solo se puede entregar un pedido en estado LISTO")
        _cambiar_estado(s, pedido, "ENTREGADO", id_usuario)


def cancelar_pedido(id_usuario, id_pedido):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        pedido = _pedido_propio(s, id_usuario, id_pedido)
        if pedido.estado == "ENTREGADO":
            raise ErrorNegocio("CANCELACION_NO_PERMITIDA", "El pedido ya fue entregado")
        if pedido.estado == "CANCELADO":
            raise ErrorNegocio("TRANSICION_INVALIDA", "El pedido ya está cancelado")
        _cambiar_estado(s, pedido, "CANCELADO", id_usuario)


# ------------------------------------------------------------------- READ
def obtener_pedido(id_usuario, id_pedido):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        pedido = s.query(Pedido).filter(Pedido.id_pedido == id_pedido,
                                        Pedido.id_usuario_mesero == id_usuario).first()
        if pedido is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido no existe o no pertenece a este mesero")
        datos = _resumen(pedido)
        datos["productos"] = [
            {"id_detalle": d.id_detalle, "producto": d.producto.nombre, "cantidad": d.cantidad,
             "precio_unitario": d.precio_unitario, "subtotal": d.cantidad * d.precio_unitario,
             "notas": d.notas}
            for d in pedido.detalles]
        return datos


def listar_pedidos(id_usuario, estado=None):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        consulta = (s.query(Pedido)
                    # selectinload evita el problema N+1 (mejor práctica de la guía)
                    .options(selectinload(Pedido.mesas), selectinload(Pedido.detalles))
                    .filter(Pedido.id_usuario_mesero == id_usuario))
        if estado:
            consulta = consulta.filter(Pedido.estado == estado)
        consulta = consulta.order_by(Pedido.fecha_creacion.desc(), Pedido.id_pedido.desc())
        return [_resumen(p) for p in consulta.all()]


def obtener_historial(id_usuario, id_pedido):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "MESERO")
        pedido = s.query(Pedido).filter(Pedido.id_pedido == id_pedido,
                                        Pedido.id_usuario_mesero == id_usuario).first()
        if pedido is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido no existe o no pertenece a este mesero")
        filas = sorted(pedido.historial, key=lambda h: (h.fecha, h.id_historial))
        return [{"estado": h.estado, "fecha": h.fecha, "usuario": h.usuario.nombre,
                 "rol": h.usuario.rol.nombre} for h in filas]


# ------------------------------------------------- utilidad de demostración
def avanzar_cocina(id_usuario_cocina, id_pedido):
    """Simula a cocina (fuera del alcance de HU-01..05) para poder demostrar HU-04."""
    with sesion() as s:
        _exigir_rol(s, id_usuario_cocina, "COCINA")
        pedido = s.query(Pedido).filter(Pedido.id_pedido == id_pedido).with_for_update().first()
        if pedido is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
        siguiente = {"PENDIENTE": "EN_PREPARACION", "EN_PREPARACION": "LISTO"}.get(pedido.estado)
        if siguiente is None:
            raise ErrorNegocio("TRANSICION_INVALIDA", f"Cocina no puede avanzar un pedido {pedido.estado}")
        if siguiente == "EN_PREPARACION" and not pedido.detalles:
            raise ErrorNegocio("PEDIDO_SIN_PRODUCTOS", "No se puede preparar un pedido sin productos")
        _cambiar_estado(s, pedido, siguiente, id_usuario_cocina)
        return siguiente
