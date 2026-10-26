"""CRUD de cocina, reportes e historial con ORM (SQLAlchemy). No hay SQL escrito a mano: se trabaja con
objetos (Pedido, HistorialEstado, DetallePedido...) y la sesión genera los INSERT/UPDATE/DELETE.

Mismas reglas de negocio y mismas funciones que la versión con driver (el ADMINISTRADOR puede ejecutar cualquier operación):
  session.add() = CREATE | session.query()/get() = READ | atributo modificado = UPDATE |
  session.delete() = DELETE | commit/rollback en db.sesion()
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import and_, func
from sqlalchemy.orm import selectinload

from db import sesion
from errores import ErrorNegocio, SIN_CAMBIO
from modelos import (Categoria, DetallePedido, HistorialEstado, Mesa, Pedido, Producto, Usuario)
from validaciones import (limpiar_notas, validar_cantidad, validar_estado, validar_fecha_hora,
                          validar_rango)

TECNOLOGIA = "ORM SQLAlchemy"
ACTIVOS = ("PENDIENTE", "EN_PREPARACION", "LISTO")
# Transiciones válidas del motor de estados (igual que sp_cambiar_estado del backend)
TRANSICIONES = {
    ("PENDIENTE", "EN_PREPARACION"), ("EN_PREPARACION", "LISTO"), ("LISTO", "ENTREGADO"),
    ("PENDIENTE", "CANCELADO"), ("EN_PREPARACION", "CANCELADO"),
}


# ------------------------------------------------------- reglas / auxiliares
def _exigir_rol(s, id_usuario, rol):
    """Valida el rol. El ADMINISTRADOR puede hacer cualquier operación. Devuelve el rol real del usuario."""
    usuario = s.get(Usuario, id_usuario)
    if (usuario is None or not usuario.activo
            or (usuario.rol.nombre != rol and usuario.rol.nombre != "ADMINISTRADOR")):
        raise ErrorNegocio("ACCESO_DENEGADO", "El usuario no tiene permiso para esta operación")
    return usuario.rol.nombre


def _pedido_bloqueado(s, id_pedido):
    """Pedido bloqueado (FOR UPDATE) que debe existir."""
    pedido = s.query(Pedido).filter(Pedido.id_pedido == id_pedido).with_for_update().first()
    if pedido is None:
        raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
    return pedido


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
    """Motor de estados: valida la transición, actualiza el pedido y registra el historial."""
    if (pedido.estado, nuevo) not in TRANSICIONES:
        raise ErrorNegocio("TRANSICION_INVALIDA", "El cambio de estado no está permitido")
    pedido.estado = nuevo
    pedido.fecha_ultima_actualizacion = func.now()
    pedido.historial.append(HistorialEstado(estado=nuevo, fecha=func.now(), id_usuario_cambio=id_usuario))
    s.flush()
    if nuevo in ("ENTREGADO", "CANCELADO"):
        _liberar_mesas(s, pedido)


def _para_cocina(p):
    return {
        "id_pedido": p.id_pedido,
        "fecha_creacion": p.fecha_creacion,
        "fecha_ultima_actualizacion": p.fecha_ultima_actualizacion,
        "mesas": sorted(m.numero for m in p.mesas),
        "productos": [{"producto": d.producto.nombre, "cantidad": d.cantidad, "notas": d.notas}
                      for d in p.detalles],
    }


def _resumen(p):
    return {
        "id_pedido": p.id_pedido, "estado": p.estado,
        "fecha_creacion": p.fecha_creacion, "fecha_ultima_actualizacion": p.fecha_ultima_actualizacion,
        "mesero": p.mesero.nombre,
        "mesas": sorted(m.numero for m in p.mesas),
        "total": p.total,
    }


# ------------------------------------------------------------------ usuarios
def buscar_usuario(login):
    with sesion() as s:
        u = s.query(Usuario).filter(Usuario.usuario_login == login, Usuario.activo.is_(True)).first()
        return None if u is None else {"id_usuario": u.id_usuario, "nombre": u.nombre, "rol": u.rol.nombre}


# =========================================================== HU-06 / 07 / 08
def ver_cola(id_usuario):
    """HU-06: pedidos PENDIENTES con al menos un producto, del más antiguo al más reciente."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "COCINA")
        pedidos = (s.query(Pedido)
                   .filter(Pedido.estado == "PENDIENTE", Pedido.detalles.any())
                   .order_by(Pedido.fecha_creacion, Pedido.id_pedido).all())
        return [_para_cocina(p) for p in pedidos]


def ver_en_preparacion(id_usuario):
    with sesion() as s:
        _exigir_rol(s, id_usuario, "COCINA")
        pedidos = (s.query(Pedido).filter(Pedido.estado == "EN_PREPARACION")
                   .order_by(Pedido.fecha_ultima_actualizacion, Pedido.id_pedido).all())
        return [_para_cocina(p) for p in pedidos]


def iniciar_preparacion(id_usuario, id_pedido):
    """HU-07: PENDIENTE -> EN_PREPARACION (el pedido debe tener productos)."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "COCINA")
        pedido = _pedido_bloqueado(s, id_pedido)
        if not pedido.detalles:
            raise ErrorNegocio("PEDIDO_VACIO", "El pedido no tiene productos")
        _cambiar_estado(s, pedido, "EN_PREPARACION", id_usuario)


def marcar_listo(id_usuario, id_pedido):
    """HU-08: EN_PREPARACION -> LISTO."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "COCINA")
        pedido = _pedido_bloqueado(s, id_pedido)
        _cambiar_estado(s, pedido, "LISTO", id_usuario)


# ================================================================== HU-13
def _limites(desde, hasta):
    """Rango [inicio del día 'desde', inicio del día siguiente a 'hasta')."""
    return datetime.combine(desde, time.min), datetime.combine(hasta + timedelta(days=1), time.min)


def reporte_ventas(id_usuario, desde, hasta, id_categoria=None, id_producto=None):
    desde, hasta = validar_rango(desde, hasta)
    inicio, fin = _limites(desde, hasta)
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        q = (s.query(Pedido.id_pedido.label("id_pedido"),
                     Producto.id_producto.label("id_producto"), Producto.nombre.label("producto"),
                     Categoria.id_categoria.label("id_categoria"), Categoria.nombre.label("categoria"),
                     DetallePedido.cantidad.label("cantidad"),
                     (DetallePedido.cantidad * DetallePedido.precio_unitario).label("subtotal"))
             .select_from(Pedido)
             .join(HistorialEstado, and_(HistorialEstado.id_pedido == Pedido.id_pedido,
                                         HistorialEstado.estado == "ENTREGADO"))
             .join(DetallePedido, DetallePedido.id_pedido == Pedido.id_pedido)
             .join(Producto, Producto.id_producto == DetallePedido.id_producto)
             .join(Categoria, Categoria.id_categoria == Producto.id_categoria)
             .filter(Pedido.estado == "ENTREGADO",
                     HistorialEstado.fecha >= inicio, HistorialEstado.fecha < fin))
        if id_categoria is not None:
            q = q.filter(Categoria.id_categoria == id_categoria)
        if id_producto is not None:
            q = q.filter(Producto.id_producto == id_producto)
        filas = q.all()
    por_categoria, por_producto = {}, {}
    for f in filas:
        c = por_categoria.setdefault(f.id_categoria, {"categoria": f.categoria,
                                                      "productos_vendidos": 0, "total_ventas": Decimal(0)})
        c["productos_vendidos"] += f.cantidad
        c["total_ventas"] += f.subtotal
        p = por_producto.setdefault(f.id_producto, {"producto": f.producto, "categoria": f.categoria,
                                                    "unidades_vendidas": 0, "total_ventas": Decimal(0)})
        p["unidades_vendidas"] += f.cantidad
        p["total_ventas"] += f.subtotal
    return {
        "resumen": {"pedidos_entregados": len({f.id_pedido for f in filas}),
                    "productos_vendidos": sum(f.cantidad for f in filas),
                    "total_ventas": sum((f.subtotal for f in filas), Decimal(0))},
        "por_categoria": sorted(por_categoria.values(), key=lambda x: x["total_ventas"], reverse=True),
        "por_producto": sorted(por_producto.values(), key=lambda x: x["total_ventas"], reverse=True),
    }


# ================================================================== HU-14
def _minutos(inicio, fin):
    if inicio is None or fin is None:
        return None
    return Decimal(str((fin - inicio).total_seconds())) / 60


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return round(sum(valores) / len(valores), 2) if valores else None


def reporte_tiempos(id_usuario, desde, hasta):
    """Tiempos calculados a partir del historial (primer registro de cada estado)."""
    desde, hasta = validar_rango(desde, hasta)
    inicio, fin = _limites(desde, hasta)
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        pedidos = (s.query(Pedido).options(selectinload(Pedido.historial))
                   .filter(Pedido.estado != "CANCELADO", Pedido.fecha_creacion >= inicio,
                           Pedido.fecha_creacion < fin).all())
        filas = []
        for p in pedidos:
            if not p.historial:
                continue
            primero = {}
            for h in p.historial:
                if h.estado not in primero or h.fecha < primero[h.estado]:
                    primero[h.estado] = h.fecha
            t_creado, t_prep = primero.get("PENDIENTE"), primero.get("EN_PREPARACION")
            t_listo, t_entregado = primero.get("LISTO"), primero.get("ENTREGADO")
            filas.append({
                "id_pedido": p.id_pedido, "t_creado": t_creado, "t_prep": t_prep,
                "t_listo": t_listo, "t_entregado": t_entregado,
                "min_espera_en_cola": _minutos(t_creado, t_prep),
                "min_preparacion": _minutos(t_prep, t_listo),
                "min_espera_entrega": _minutos(t_listo, t_entregado),
                "min_total": _minutos(t_creado, t_entregado),
            })
    filas.sort(key=lambda f: (f["t_creado"] is None, f["t_creado"], f["id_pedido"]))
    return {
        "detalle": filas,
        "promedios": {
            "pedidos_preparados": sum(1 for f in filas if f["t_listo"] is not None),
            "prom_min_espera_en_cola": _promedio([f["min_espera_en_cola"] for f in filas]),
            "prom_min_preparacion": _promedio([f["min_preparacion"] for f in filas]),
            "prom_min_espera_entrega": _promedio([f["min_espera_entrega"] for f in filas]),
            "prom_min_total": _promedio([f["min_total"] for f in filas]),
        },
    }


# ================================================== HU-15 historial (CRUD)
def _hist_dict(h):
    return {"id_historial": h.id_historial, "id_pedido": h.id_pedido, "estado": h.estado, "fecha": h.fecha,
            "id_usuario_cambio": h.id_usuario_cambio, "usuario": h.usuario.nombre, "rol": h.usuario.rol.nombre}


def _historial_o_error(s, id_historial):
    h = s.get(HistorialEstado, id_historial)
    if h is None:
        raise ErrorNegocio("HISTORIAL_NO_EXISTE", "El registro de historial no existe")
    return h


def _exigir_usuario_existente(s, id_usuario):
    if s.get(Usuario, id_usuario) is None:
        raise ErrorNegocio("USUARIO_NO_EXISTE", "El usuario indicado no existe")


def listar_historial(id_usuario, id_pedido=None):
    """READ (lista): todo el historial o el de un pedido."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        q = s.query(HistorialEstado)
        if id_pedido is not None:
            q = q.filter(HistorialEstado.id_pedido == id_pedido)
        registros = q.order_by(HistorialEstado.id_pedido, HistorialEstado.fecha,
                               HistorialEstado.id_historial).all()
        return [_hist_dict(h) for h in registros]


def obtener_historial(id_usuario, id_historial):
    """READ (uno)."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        return _hist_dict(_historial_o_error(s, id_historial))


def crear_historial(id_usuario, id_pedido, estado, fecha=None, id_usuario_cambio=None):
    """CREATE: fecha (por defecto ahora) y usuario (por defecto quien lo crea) son opcionales."""
    estado = validar_estado(estado)
    fecha = validar_fecha_hora(fecha) if fecha is not None else None
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        if s.get(Pedido, id_pedido) is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
        autor = id_usuario_cambio or id_usuario
        _exigir_usuario_existente(s, autor)
        h = HistorialEstado(id_pedido=id_pedido, estado=estado,
                            fecha=fecha if fecha is not None else func.now(), id_usuario_cambio=autor)
        s.add(h)
        s.flush()                                  # genera el id_historial
        return h.id_historial


def editar_historial(id_usuario, id_historial, estado=SIN_CAMBIO, fecha=SIN_CAMBIO, id_usuario_cambio=SIN_CAMBIO):
    """UPDATE: solo se modifican los campos enviados (los SIN_CAMBIO se conservan)."""
    if estado is SIN_CAMBIO and fecha is SIN_CAMBIO and id_usuario_cambio is SIN_CAMBIO:
        raise ErrorNegocio("CAMPO_REQUERIDO", "Indique al menos un dato para editar")
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        h = _historial_o_error(s, id_historial)
        if estado is not SIN_CAMBIO:
            h.estado = validar_estado(estado)
        if fecha is not SIN_CAMBIO:
            h.fecha = validar_fecha_hora(fecha)
        if id_usuario_cambio is not SIN_CAMBIO:
            _exigir_usuario_existente(s, id_usuario_cambio)
            h.id_usuario_cambio = id_usuario_cambio


def eliminar_historial(id_usuario, id_historial):
    """DELETE."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        s.delete(_historial_o_error(s, id_historial))


# ============================================ apoyo (HU de mesero / admin)
def listar_menu(id_usuario):
    with sesion() as s:
        rol = _exigir_rol(s, id_usuario, "MESERO")
        productos = s.query(Producto).filter(Producto.disponibilidad.is_(True)).all()
        productos.sort(key=lambda p: (p.categoria.nombre, p.nombre))
        return [{"categoria": p.categoria.nombre, "id_producto": p.id_producto, "nombre": p.nombre,
                 "descripcion": p.descripcion, "precio": p.precio} for p in productos]


def listar_mesas_libres(id_usuario):
    with sesion() as s:
        rol = _exigir_rol(s, id_usuario, "MESERO")
        mesas = s.query(Mesa).filter(Mesa.estado == "libre").order_by(Mesa.numero).all()
        return [{"id_mesa": m.id_mesa, "numero": m.numero} for m in mesas]


def crear_pedido(id_usuario, id_mesa):
    """HU-01 (apoyo)."""
    with sesion() as s:
        rol = _exigir_rol(s, id_usuario, "MESERO")
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


def agregar_producto(id_usuario, id_pedido, id_producto, cantidad, notas=None):
    """HU-02 (apoyo): un renglón por producto; si ya estaba, se suma la cantidad."""
    notas = limpiar_notas(notas)
    with sesion() as s:
        rol = _exigir_rol(s, id_usuario, "MESERO")
        validar_cantidad(cantidad)
        pedido = _pedido_bloqueado(s, id_pedido)
        if rol != "ADMINISTRADOR" and pedido.id_usuario_mesero != id_usuario:
            raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
        if pedido.estado != "PENDIENTE":
            raise ErrorNegocio("PEDIDO_BLOQUEADO", "Solo se puede editar un pedido en estado PENDIENTE")
        producto = s.get(Producto, id_producto)
        if producto is None:
            raise ErrorNegocio("PRODUCTO_NO_EXISTE", "El producto indicado no existe")
        if not producto.disponibilidad:
            raise ErrorNegocio("PRODUCTO_NO_DISPONIBLE", "El producto no está disponible")
        detalle = next((d for d in pedido.detalles if d.id_producto == id_producto), None)
        if detalle:
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


def marcar_entregado(id_usuario, id_pedido):
    """HU-04 (apoyo)."""
    with sesion() as s:
        rol = _exigir_rol(s, id_usuario, "MESERO")
        pedido = _pedido_bloqueado(s, id_pedido)
        if rol != "ADMINISTRADOR" and pedido.id_usuario_mesero != id_usuario:
            raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
        if pedido.estado != "LISTO":
            raise ErrorNegocio("TRANSICION_INVALIDA", "Solo se puede entregar un pedido en estado LISTO")
        _cambiar_estado(s, pedido, "ENTREGADO", id_usuario)


def cancelar_pedido(id_usuario, id_pedido):
    """HU-05 (apoyo): desde PENDIENTE o EN_PREPARACION (igual que el backend del grupo)."""
    with sesion() as s:
        rol = _exigir_rol(s, id_usuario, "MESERO")
        pedido = _pedido_bloqueado(s, id_pedido)
        if rol != "ADMINISTRADOR" and pedido.id_usuario_mesero != id_usuario:
            raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
        if pedido.estado == "ENTREGADO":
            raise ErrorNegocio("CANCELACION_NO_PERMITIDA", "El pedido ya fue entregado")
        _cambiar_estado(s, pedido, "CANCELADO", id_usuario)


def listar_pedidos(id_usuario, estado=None):
    """Todos los pedidos (administrador)."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        q = s.query(Pedido)
        if estado:
            q = q.filter(Pedido.estado == validar_estado(estado))
        pedidos = q.order_by(Pedido.fecha_creacion.desc(), Pedido.id_pedido.desc()).all()
        return [_resumen(p) for p in pedidos]


def obtener_pedido(id_usuario, id_pedido):
    """Un pedido con sus productos (administrador)."""
    with sesion() as s:
        _exigir_rol(s, id_usuario, "ADMINISTRADOR")
        pedido = s.get(Pedido, id_pedido)
        if pedido is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
        resumen = _resumen(pedido)
        resumen["productos"] = [
            {"id_detalle": d.id_detalle, "producto": d.producto.nombre, "cantidad": d.cantidad,
             "precio_unitario": d.precio_unitario, "subtotal": d.cantidad * d.precio_unitario,
             "notas": d.notas} for d in pedido.detalles]
        return resumen
