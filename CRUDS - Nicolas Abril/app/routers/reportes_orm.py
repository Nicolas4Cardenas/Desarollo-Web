"""Reportes (HU-13 ventas, HU-14 tiempos) con ORM (SQLAlchemy). Las mismas consultas
del procedimiento / de la version con driver, pero armadas con select(), join(),
group_by() y func.* sobre las clases de models.py."""
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, distinct, func, literal_column, select
from sqlalchemy.orm import Session

from app.models import (
    Categoria,
    DetallePedido,
    HistorialEstado,
    Pedido,
    Producto,
    Usuario,
)
from app.orm_db import get_session

router = APIRouter(prefix="/orm/reportes", tags=["Reportes (ORM)"])

SEGUNDOS = literal_column("SECOND")  # unidad que pide TIMESTAMPDIFF


def validar_rol_admin(session: Session, id_usuario: int):
    usuario = session.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo or usuario.rol.nombre != "ADMINISTRADOR":
        raise HTTPException(
            status_code=403,
            detail="ACCESO_DENEGADO: el usuario no tiene permiso para esta operación",
        )


def rango_datetime(desde: date, hasta: date):
    """Devuelve (inicio, fin_exclusivo) para que el rango incluya todo el dia 'hasta'."""
    if hasta < desde:
        raise HTTPException(
            status_code=400, detail="RANGO_INVALIDO: revise las fechas del reporte"
        )
    inicio = datetime.combine(desde, time.min)
    fin = datetime.combine(hasta + timedelta(days=1), time.min)
    return inicio, fin


@router.get("/ventas")
def reporte_ventas(
    id_usuario: int,
    desde: date,
    hasta: date,
    id_categoria: Optional[int] = None,
    id_producto: Optional[int] = None,
    session: Session = Depends(get_session),
):
    validar_rol_admin(session, id_usuario)
    inicio, fin = rango_datetime(desde, hasta)

    # Condiciones: solo pedidos ENTREGADOS cuya fecha de entrega cae en el rango
    condiciones = [
        Pedido.estado == "ENTREGADO",
        HistorialEstado.fecha >= inicio,
        HistorialEstado.fecha < fin,
    ]
    if id_categoria is not None:
        condiciones.append(Categoria.id_categoria == id_categoria)
    if id_producto is not None:
        condiciones.append(Producto.id_producto == id_producto)

    def consulta(*columnas):
        """Misma base (joins + condiciones) para los tres resultados."""
        return (
            select(*columnas)
            .select_from(Pedido)
            .join(
                HistorialEstado,
                and_(
                    HistorialEstado.id_pedido == Pedido.id_pedido,
                    HistorialEstado.estado == "ENTREGADO",
                ),
            )
            .join(DetallePedido, DetallePedido.id_pedido == Pedido.id_pedido)
            .join(Producto, Producto.id_producto == DetallePedido.id_producto)
            .join(Categoria, Categoria.id_categoria == Producto.id_categoria)
            .where(*condiciones)
        )

    unidades = func.sum(DetallePedido.cantidad)
    ventas = func.sum(DetallePedido.cantidad * DetallePedido.precio_unitario)

    totales = session.execute(
        consulta(
            func.count(distinct(Pedido.id_pedido)).label("pedidos_entregados"),
            func.coalesce(unidades, 0).label("productos_vendidos"),
            func.coalesce(ventas, 0).label("total_ventas"),
        )
    ).one()

    por_categoria = session.execute(
        consulta(
            Categoria.nombre.label("categoria"),
            unidades.label("productos_vendidos"),
            ventas.label("total_ventas"),
        )
        .group_by(Categoria.id_categoria, Categoria.nombre)
        .order_by(ventas.desc())
    ).all()

    por_producto = session.execute(
        consulta(
            Producto.nombre.label("producto"),
            Categoria.nombre.label("categoria"),
            unidades.label("unidades_vendidas"),
            ventas.label("total_ventas"),
        )
        .group_by(Producto.id_producto, Producto.nombre, Categoria.nombre)
        .order_by(ventas.desc())
    ).all()

    return {
        "desde": desde,
        "hasta": hasta,
        "totales": dict(totales._mapping),
        "por_categoria": [dict(f._mapping) for f in por_categoria],
        "por_producto": [dict(f._mapping) for f in por_producto],
    }


@router.get("/tiempos")
def reporte_tiempos(
    id_usuario: int,
    desde: date,
    hasta: date,
    session: Session = Depends(get_session),
):
    validar_rol_admin(session, id_usuario)
    inicio, fin = rango_datetime(desde, hasta)

    def primera_vez(estado: str):
        """Primera fecha en que el pedido paso por ese estado."""
        return func.min(case((HistorialEstado.estado == estado, HistorialEstado.fecha)))

    # Un renglon por pedido (no cancelado): equivale a la tabla temporal tmp_tiempos
    t = (
        select(
            Pedido.id_pedido.label("id_pedido"),
            primera_vez("PENDIENTE").label("t_creado"),
            primera_vez("EN_PREPARACION").label("t_prep"),
            primera_vez("LISTO").label("t_listo"),
            primera_vez("ENTREGADO").label("t_entregado"),
        )
        .select_from(Pedido)
        .join(HistorialEstado, HistorialEstado.id_pedido == Pedido.id_pedido)
        .where(
            Pedido.estado != "CANCELADO",
            Pedido.fecha_creacion >= inicio,
            Pedido.fecha_creacion < fin,
        )
        .group_by(Pedido.id_pedido)
        .subquery("t")
    )

    def segundos(desde_col, hasta_col):
        return func.timestampdiff(SEGUNDOS, desde_col, hasta_col)

    por_pedido = session.execute(
        select(
            t.c.id_pedido,
            t.c.t_creado,
            t.c.t_prep,
            t.c.t_listo,
            t.c.t_entregado,
            (segundos(t.c.t_creado, t.c.t_prep) / 60).label("min_espera_en_cola"),
            (segundos(t.c.t_prep, t.c.t_listo) / 60).label("min_preparacion"),
            (segundos(t.c.t_listo, t.c.t_entregado) / 60).label("min_espera_entrega"),
            (segundos(t.c.t_creado, t.c.t_entregado) / 60).label("min_total"),
        ).order_by(t.c.t_creado, t.c.id_pedido)
    ).all()

    promedio = session.execute(
        select(
            func.count(t.c.t_listo).label("pedidos_preparados"),
            func.round(func.avg(segundos(t.c.t_creado, t.c.t_prep)) / 60, 2).label(
                "prom_min_espera_en_cola"
            ),
            func.round(func.avg(segundos(t.c.t_prep, t.c.t_listo)) / 60, 2).label(
                "prom_min_preparacion"
            ),
            func.round(func.avg(segundos(t.c.t_listo, t.c.t_entregado)) / 60, 2).label(
                "prom_min_espera_entrega"
            ),
            func.round(func.avg(segundos(t.c.t_creado, t.c.t_entregado)) / 60, 2).label(
                "prom_min_total"
            ),
        )
    ).one()

    return {
        "desde": desde,
        "hasta": hasta,
        "por_pedido": [dict(f._mapping) for f in por_pedido],
        "promedio_periodo": dict(promedio._mapping),
    }
