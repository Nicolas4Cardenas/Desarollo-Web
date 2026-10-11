from fastapi import APIRouter
from pydantic import BaseModel
from app.db import llamar_sp

router = APIRouter(prefix="/cocina/pedidos", tags=["Cocina"])


class CambioEstado(BaseModel):
    id_usuario: int


@router.get("")
def ver_cola(id_usuario: int):
    pedidos, detalle = llamar_sp("sp_cocina_ver_cola", [id_usuario])
    for p in pedidos:
        p["detalle"] = [
            {k: v for k, v in d.items() if k != "id_pedido"}
            for d in detalle
            if d["id_pedido"] == p["id_pedido"]
        ]
    return pedidos


@router.put("/{id_pedido}/en-preparacion")
def iniciar_preparacion(id_pedido: int, datos: CambioEstado):
    llamar_sp("sp_cocina_iniciar_preparacion", [datos.id_usuario, id_pedido])
    return {"id_pedido": id_pedido, "estado": "EN_PREPARACION"}


@router.put("/{id_pedido}/listo")
def marcar_listo(id_pedido: int, datos: CambioEstado):
    llamar_sp("sp_cocina_marcar_listo", [datos.id_usuario, id_pedido])
    return {"id_pedido": id_pedido, "estado": "LISTO"}