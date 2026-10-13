"""Cocina (HU-06, HU-07, HU-08) con ORM (SQLAlchemy). No hay SQL escrito a mano ni
procedimientos: se consulta y se modifica a traves de las clases de models.py.
Las reglas (rol, transiciones, historial) se aplican aqui, dentro de una transaccion."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import DetallePedido, HistorialEstado, Pedido, Usuario
from app.orm_db import get_session

router = APIRouter(prefix="/orm/cocina/pedidos", tags=["Cocina (ORM)"])

# Transiciones que puede hacer cocina: estado nuevo -> estado actual requerido
ESTADO_PREVIO = {
    "EN_PREPARACION": "PENDIENTE",
    "LISTO": "EN_PREPARACION",
}


class CambioEstado(BaseModel):
    id_usuario: int


def validar_rol_cocina(session: Session, id_usuario: int):
    """El usuario debe existir, estar activo y tener el rol COCINA."""
    usuario = session.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo or usuario.rol.nombre != "COCINA":
        raise HTTPException(
            status_code=403,
            detail="ACCESO_DENEGADO: el usuario no tiene permiso para esta operación",
        )


def cambiar_estado(session: Session, id_pedido: int, id_usuario: int, nuevo: str):
    validar_rol_cocina(session, id_usuario)

    # with_for_update() = SELECT ... FOR UPDATE: bloquea la fila durante la transaccion
    pedido = session.scalars(
        select(Pedido).where(Pedido.id_pedido == id_pedido).with_for_update()
    ).one_or_none()
    if pedido is None:
        raise HTTPException(
            status_code=404, detail="PEDIDO_NO_EXISTE: el pedido indicado no existe"
        )
    if pedido.estado != ESTADO_PREVIO[nuevo]:
        raise HTTPException(
            status_code=409,
            detail="TRANSICION_INVALIDA: el cambio de estado no está permitido",
        )

    if nuevo == "EN_PREPARACION":
        items = session.scalar(
            select(func.count()).select_from(DetallePedido).where(
                DetallePedido.id_pedido == id_pedido
            )
        )
        if items == 0:
            raise HTTPException(
                status_code=409, detail="PEDIDO_VACIO: el pedido no tiene productos"
            )

    pedido.estado = nuevo
    pedido.fecha_ultima_actualizacion = func.now()
    session.add(
        HistorialEstado(
            id_pedido=id_pedido,
            estado=nuevo,
            fecha=func.now(),
            id_usuario_cambio=id_usuario,
        )
    )
    session.commit()  # guarda el pedido y el historial juntos
    return {"id_pedido": id_pedido, "estado": nuevo}


@router.get("")
def ver_cola(id_usuario: int, session: Session = Depends(get_session)):
    """HU-06: pedidos PENDIENTES (con al menos un producto), del mas antiguo al mas nuevo."""
    validar_rol_cocina(session, id_usuario)

    pedidos = session.scalars(
        select(Pedido)
        .where(Pedido.estado == "PENDIENTE", Pedido.detalles.any())
        .options(
            # carga las relaciones por adelantado para no hacer una consulta por pedido
            selectinload(Pedido.detalles).joinedload(DetallePedido.producto),
            selectinload(Pedido.mesas),
        )
        .order_by(Pedido.fecha_creacion, Pedido.id_pedido)
    ).all()

    return [
        {
            "id_pedido": p.id_pedido,
            "fecha_creacion": p.fecha_creacion,
            "mesas": ",".join(str(m.numero) for m in sorted(p.mesas, key=lambda m: m.numero))
            or None,
            "detalle": [
                {"producto": d.producto.nombre, "cantidad": d.cantidad, "notas": d.notas}
                for d in p.detalles
            ],
        }
        for p in pedidos
    ]


@router.put("/{id_pedido}/en-preparacion")
def iniciar_preparacion(
    id_pedido: int, datos: CambioEstado, session: Session = Depends(get_session)
):
    """HU-07: PENDIENTE -> EN_PREPARACION."""
    return cambiar_estado(session, id_pedido, datos.id_usuario, "EN_PREPARACION")


@router.put("/{id_pedido}/listo")
def marcar_listo(
    id_pedido: int, datos: CambioEstado, session: Session = Depends(get_session)
):
    """HU-08: EN_PREPARACION -> LISTO."""
    return cambiar_estado(session, id_pedido, datos.id_usuario, "LISTO")
