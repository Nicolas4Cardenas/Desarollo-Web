"""Capa de acceso a datos de los REPORTES del administrador (HU-13 y HU-14)."""
from api.dao.comun import conjuntos
from api.db import conexion


def reporte_ventas(id_admin, desde, hasta, id_categoria, id_producto):
    """HU-13. Resultado 1: totales | 2: por categoría | 3: por producto."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_reporte_ventas(%s, %s, %s, %s, %s)",
                    (id_admin, desde, hasta, id_categoria, id_producto))
        r = conjuntos(cur)
        return {
            "resumen": r[0][0] if r[0] else {},
            "por_categoria": r[1] if len(r) > 1 else [],
            "por_producto": r[2] if len(r) > 2 else [],
        }


def reporte_tiempos(id_admin, desde, hasta):
    """HU-14. Resultado 1: detalle por pedido | 2: promedios del periodo (minutos)."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_reporte_tiempos(%s, %s, %s)", (id_admin, desde, hasta))
        r = conjuntos(cur)
        return {
            "detalle": r[0],
            "promedios": r[1][0] if len(r) > 1 and r[1] else {},
        }
