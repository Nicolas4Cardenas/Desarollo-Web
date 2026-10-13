"""Historial de estados (HU-15) con ORM (SQLAlchemy): CRUD sobre la clase HistorialEstado.
Igual que la version con driver, el historial es INMUTABLE (RNF-11): editar y borrar
se rechazan en la API y, ademas, los triggers de la base los bloquean."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HistorialEstado, Pedido, Usuario
from app.orm_db import get_session

router = APIRouter(prefix="/orm/historial", tags=["Historial de estados (ORM)"])

ESTADOS_VALIDOS = ["PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO"]


class HistorialCrear(BaseModel):
    id_pedido: int
    estado: str
    id_usuario_cambio: int


def a_dict(h: HistorialEstado) -> dict:
    return {
        "id_historial": h.id_historial,
        "id_pedido": h.id_pedido,
        "estado": h.estado,
        "fecha": h.fecha,
        "id_usuario_cambio": h.id_usuario_cambio,
    }


@router.post("", status_code=201)
def crear_registro(datos: HistorialCrear, session: Session = Depends(get_session)):
    """CREATE: agrega un registro al historial."""
    if datos.estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no válido. Use uno de: {ESTADOS_VALIDOS}",
        )
    if session.get(Pedido, datos.id_pedido) is None:
        raise HTTPException(status_code=404, detail="El pedido no existe")
    if session.get(Usuario, datos.id_usuario_cambio) is None:
        raise HTTPException(status_code=404, detail="El usuario no existe")

    registro = HistorialEstado(
        id_pedido=datos.id_pedido,
        estado=datos.estado,
        id_usuario_cambio=datos.id_usuario_cambio,
    )
    session.add(registro)
    session.commit()
    session.refresh(registro)  # vuelve a leer la fila para traer id_historial y fecha
    return a_dict(registro)


@router.get("")
def listar_registros(
    id_pedido: Optional[int] = None, session: Session = Depends(get_session)
):
    """READ (lista): todos los registros, o solo los de un pedido."""
    consulta = select(HistorialEstado).order_by(
        HistorialEstado.fecha, HistorialEstado.id_historial
    )
    if id_pedido is not None:
        consulta = consulta.where(HistorialEstado.id_pedido == id_pedido)
    return [a_dict(h) for h in session.scalars(consulta).all()]


@router.get("/{id_historial}")
def obtener_registro(id_historial: int, session: Session = Depends(get_session)):
    """READ (uno): un registro por su id."""
    registro = session.get(HistorialEstado, id_historial)
    if registro is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return a_dict(registro)


@router.put("/{id_historial}")
def actualizar_registro(id_historial: int):
    """UPDATE: bloqueado, el historial no se edita."""
    raise HTTPException(
        status_code=403,
        detail="El historial es inmutable (RNF-11): no se puede editar",
    )


@router.delete("/{id_historial}")
def borrar_registro(id_historial: int):
    """DELETE: bloqueado, el historial no se borra."""
    raise HTTPException(
        status_code=403,
        detail="El historial es inmutable (RNF-11): no se puede borrar",
    )
