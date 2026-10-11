"""Reportes (HU-13 ventas, HU-14 tiempos) con acceso DIRECTO A LAS TABLAS usando el
driver mysql-connector. No llama procedimientos almacenados: las consultas que en
sp_admin_reporte_ventas / sp_admin_reporte_tiempos usaban tablas temporales se
escriben aqui como SELECT con GROUP BY y subconsultas."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.db import get_connection

router = APIRouter(prefix="/driver/reportes", tags=["Reportes (driver)"])


def validar_rol_admin(cur, id_usuario: int):
    """Equivale a sp_validar_rol(id, 'ADMINISTRADOR')."""
    cur.execute(
        "SELECT r.nombre AS rol FROM usuario u "
        "JOIN rol r ON r.id_rol = u.id_rol "
        "WHERE u.id_usuario = %s AND u.activo = TRUE",
        (id_usuario,),
    )
    fila = cur.fetchone()
    if fila is None or fila["rol"] != "ADMINISTRADOR":
        raise HTTPException(
            status_code=403,
            detail="ACCESO_DENEGADO: el usuario no tiene permiso para esta operación",
        )


def validar_rango(desde: date, hasta: date):
    if desde is None or hasta is None or hasta < desde:
        raise HTTPException(
            status_code=400,
            detail="RANGO_INVALIDO: revise las fechas del reporte",
        )


# Filas base de ventas: una por renglon de pedido ENTREGADO cuya fecha de entrega
# (en historial_estado) cae dentro del rango. Se reutiliza en los tres resultados.
VENTAS_FROM = """
    FROM pedido p
    JOIN historial_estado h ON h.id_pedido = p.id_pedido AND h.estado = 'ENTREGADO'
    JOIN detalle_pedido d   ON d.id_pedido = p.id_pedido
    JOIN producto pr        ON pr.id_producto = d.id_producto
    JOIN categoria c        ON c.id_categoria = pr.id_categoria
    WHERE p.estado = 'ENTREGADO'
      AND h.fecha >= %s AND h.fecha < %s
      AND (%s IS NULL OR c.id_categoria = %s)
      AND (%s IS NULL OR pr.id_producto = %s)
"""


@router.get("/ventas")
def reporte_ventas(
    id_usuario: int,
    desde: date,
    hasta: date,
    id_categoria: Optional[int] = None,
    id_producto: Optional[int] = None,
):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        validar_rol_admin(cur, id_usuario)
        validar_rango(desde, hasta)

        # el rango incluye todo el dia "hasta": fecha < hasta + 1 dia
        params = (
            desde, hasta + timedelta(days=1),
            id_categoria, id_categoria,
            id_producto, id_producto,
        )

        cur.execute(
            "SELECT COUNT(DISTINCT p.id_pedido) AS pedidos_entregados, "
            "       COALESCE(SUM(d.cantidad), 0) AS productos_vendidos, "
            "       COALESCE(SUM(d.cantidad * d.precio_unitario), 0) AS total_ventas "
            + VENTAS_FROM,
            params,
        )
        totales = cur.fetchone()

        cur.execute(
            "SELECT c.nombre AS categoria, SUM(d.cantidad) AS productos_vendidos, "
            "       SUM(d.cantidad * d.precio_unitario) AS total_ventas "
            + VENTAS_FROM
            + " GROUP BY c.id_categoria, c.nombre ORDER BY total_ventas DESC",
            params,
        )
        por_categoria = cur.fetchall()

        cur.execute(
            "SELECT pr.nombre AS producto, c.nombre AS categoria, "
            "       SUM(d.cantidad) AS unidades_vendidas, "
            "       SUM(d.cantidad * d.precio_unitario) AS total_ventas "
            + VENTAS_FROM
            + " GROUP BY pr.id_producto, pr.nombre, c.nombre ORDER BY total_ventas DESC",
            params,
        )
        por_producto = cur.fetchall()

        return {
            "desde": desde,
            "hasta": hasta,
            "totales": totales,
            "por_categoria": por_categoria,
            "por_producto": por_producto,
        }
    finally:
        cur.close()
        conn.close()


# Un renglon por pedido (no cancelado) con la primera vez que paso por cada estado.
# Es la tabla temporal tmp_tiempos del procedimiento, aqui como subconsulta.
TIEMPOS_BASE = """
    SELECT p.id_pedido,
           MIN(CASE WHEN h.estado = 'PENDIENTE'      THEN h.fecha END) AS t_creado,
           MIN(CASE WHEN h.estado = 'EN_PREPARACION' THEN h.fecha END) AS t_prep,
           MIN(CASE WHEN h.estado = 'LISTO'          THEN h.fecha END) AS t_listo,
           MIN(CASE WHEN h.estado = 'ENTREGADO'      THEN h.fecha END) AS t_entregado
      FROM pedido p JOIN historial_estado h ON h.id_pedido = p.id_pedido
     WHERE p.estado <> 'CANCELADO'
       AND p.fecha_creacion >= %s
       AND p.fecha_creacion <  %s
     GROUP BY p.id_pedido
"""


@router.get("/tiempos")
def reporte_tiempos(id_usuario: int, desde: date, hasta: date):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        validar_rol_admin(cur, id_usuario)
        validar_rango(desde, hasta)
        params = (desde, hasta + timedelta(days=1))

        cur.execute(
            "SELECT id_pedido, t_creado, t_prep, t_listo, t_entregado, "
            "  TIMESTAMPDIFF(SECOND, t_creado, t_prep)       / 60 AS min_espera_en_cola, "
            "  TIMESTAMPDIFF(SECOND, t_prep,  t_listo)       / 60 AS min_preparacion, "
            "  TIMESTAMPDIFF(SECOND, t_listo, t_entregado)   / 60 AS min_espera_entrega, "
            "  TIMESTAMPDIFF(SECOND, t_creado, t_entregado)  / 60 AS min_total "
            "FROM (" + TIEMPOS_BASE + ") t ORDER BY t_creado, id_pedido",
            params,
        )
        por_pedido = cur.fetchall()

        cur.execute(
            "SELECT COUNT(t_listo) AS pedidos_preparados, "
            "  ROUND(AVG(TIMESTAMPDIFF(SECOND, t_creado, t_prep)) / 60, 2)     AS prom_min_espera_en_cola, "
            "  ROUND(AVG(TIMESTAMPDIFF(SECOND, t_prep,  t_listo)) / 60, 2)     AS prom_min_preparacion, "
            "  ROUND(AVG(TIMESTAMPDIFF(SECOND, t_listo, t_entregado)) / 60, 2) AS prom_min_espera_entrega, "
            "  ROUND(AVG(TIMESTAMPDIFF(SECOND, t_creado, t_entregado)) / 60, 2) AS prom_min_total "
            "FROM (" + TIEMPOS_BASE + ") t",
            params,
        )
        promedio = cur.fetchone()

        return {
            "desde": desde,
            "hasta": hasta,
            "por_pedido": por_pedido,
            "promedio_periodo": promedio,
        }
    finally:
        cur.close()
        conn.close()
