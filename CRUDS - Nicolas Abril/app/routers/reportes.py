from datetime import date
from typing import Optional
from fastapi import APIRouter
from app.db import llamar_sp

router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.get("/ventas")
def reporte_ventas(
    id_usuario: int,
    desde: date,
    hasta: date,
    id_categoria: Optional[int] = None,
    id_producto: Optional[int] = None,
):
    totales, por_categoria, por_producto = llamar_sp(
        "sp_admin_reporte_ventas",
        [id_usuario, desde, hasta, id_categoria, id_producto],
    )
    return {
        "desde": desde,
        "hasta": hasta,
        "totales": totales[0],
        "por_categoria": por_categoria,
        "por_producto": por_producto,
    }


@router.get("/tiempos")
def reporte_tiempos(id_usuario: int, desde: date, hasta: date):
    por_pedido, promedio = llamar_sp(
        "sp_admin_reporte_tiempos", [id_usuario, desde, hasta]
    )
    return {
        "desde": desde,
        "hasta": hasta,
        "por_pedido": por_pedido,
        "promedio_periodo": promedio[0],
    }