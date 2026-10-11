from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db import get_connection

router = APIRouter(prefix="/historial", tags=["Historial de estados"])

ESTADOS_VALIDOS = ["PENDIENTE", "EN_PREPARACION", "LISTO", "ENTREGADO", "CANCELADO"]


class HistorialCrear(BaseModel):
    id_pedido: int
    estado: str
    id_usuario_cambio: int


@router.post("", status_code=201)
def crear_registro(datos: HistorialCrear):
    if datos.estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado no válido. Use uno de: {ESTADOS_VALIDOS}",
        )
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT 1 FROM pedido WHERE id_pedido = %s", (datos.id_pedido,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="El pedido no existe")

        cur.execute(
            "SELECT 1 FROM usuario WHERE id_usuario = %s",
            (datos.id_usuario_cambio,),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="El usuario no existe")

        cur.execute(
            "INSERT INTO historial_estado (id_pedido, estado, id_usuario_cambio) "
            "VALUES (%s, %s, %s)",
            (datos.id_pedido, datos.estado, datos.id_usuario_cambio),
        )
        conn.commit()
        cur.execute(
            "SELECT * FROM historial_estado WHERE id_historial = %s",
            (cur.lastrowid,),
        )
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


@router.get("")
def listar_registros(id_pedido: Optional[int] = None):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        if id_pedido is None:
            cur.execute("SELECT * FROM historial_estado ORDER BY fecha, id_historial")
        else:
            cur.execute(
                "SELECT * FROM historial_estado WHERE id_pedido = %s "
                "ORDER BY fecha, id_historial",
                (id_pedido,),
            )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@router.get("/{id_historial}")
def obtener_registro(id_historial: int):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT * FROM historial_estado WHERE id_historial = %s",
            (id_historial,),
        )
        fila = cur.fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        return fila
    finally:
        cur.close()
        conn.close()


@router.put("/{id_historial}")
def actualizar_registro(id_historial: int):
    raise HTTPException(
        status_code=403,
        detail="El historial es inmutable (RNF-11): no se puede editar",
    )


@router.delete("/{id_historial}")
def borrar_registro(id_historial: int):
    raise HTTPException(
        status_code=403,
        detail="El historial es inmutable (RNF-11): no se puede borrar",
    )