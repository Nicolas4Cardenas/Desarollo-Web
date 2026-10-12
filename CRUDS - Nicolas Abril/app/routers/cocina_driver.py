"""Cocina (HU-06, HU-07, HU-08) con acceso DIRECTO A LAS TABLAS usando el driver
mysql-connector. No llama procedimientos almacenados: las reglas que en el otro
router vivian en la base de datos (rol, transiciones, historial) se escriben aqui,
dentro de una transaccion."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_connection

router = APIRouter(prefix="/driver/cocina/pedidos", tags=["Cocina (driver)"])

# Transiciones que puede hacer cocina: estado nuevo -> estado actual requerido
TRANSICIONES_COCINA = {
    "EN_PREPARACION": "PENDIENTE",
    "LISTO": "EN_PREPARACION",
}


class CambioEstado(BaseModel):
    id_usuario: int


def validar_rol_cocina(cur, id_usuario: int):
    """Equivale a sp_validar_rol(id, 'COCINA'): el usuario debe existir, estar activo y ser COCINA."""
    cur.execute(
        "SELECT r.nombre AS rol FROM usuario u "
        "JOIN rol r ON r.id_rol = u.id_rol "
        "WHERE u.id_usuario = %s AND u.activo = TRUE",
        (id_usuario,),
    )
    fila = cur.fetchone()
    if fila is None or fila["rol"] != "COCINA":
        raise HTTPException(
            status_code=403,
            detail="ACCESO_DENEGADO: el usuario no tiene permiso para esta operación",
        )


def cambiar_estado(id_pedido: int, id_usuario: int, nuevo: str):
    """Cambia el estado de un pedido y registra el historial, todo en una transaccion."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        validar_rol_cocina(cur, id_usuario)

        # FOR UPDATE bloquea la fila para que dos cocineros no cambien el mismo pedido a la vez
        cur.execute(
            "SELECT estado FROM pedido WHERE id_pedido = %s FOR UPDATE", (id_pedido,)
        )
        pedido = cur.fetchone()
        if pedido is None:
            raise HTTPException(
                status_code=404, detail="PEDIDO_NO_EXISTE: el pedido indicado no existe"
            )
        if pedido["estado"] != TRANSICIONES_COCINA[nuevo]:
            raise HTTPException(
                status_code=409,
                detail="TRANSICION_INVALIDA: el cambio de estado no está permitido",
            )

        if nuevo == "EN_PREPARACION":
            cur.execute(
                "SELECT COUNT(*) AS items FROM detalle_pedido WHERE id_pedido = %s",
                (id_pedido,),
            )
            if cur.fetchone()["items"] == 0:
                raise HTTPException(
                    status_code=409,
                    detail="PEDIDO_VACIO: el pedido no tiene productos",
                )

        cur.execute(
            "UPDATE pedido SET estado = %s, fecha_ultima_actualizacion = NOW() "
            "WHERE id_pedido = %s",
            (nuevo, id_pedido),
        )
        cur.execute(
            "INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio) "
            "VALUES (%s, %s, NOW(), %s)",
            (id_pedido, nuevo, id_usuario),
        )
        conn.commit()
        return {"id_pedido": id_pedido, "estado": nuevo}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


@router.get("")
def ver_cola(id_usuario: int):
    """HU-06: pedidos PENDIENTES (con al menos un producto), del mas antiguo al mas nuevo."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        validar_rol_cocina(cur, id_usuario)

        cur.execute(
            "SELECT p.id_pedido, p.fecha_creacion, "
            "  (SELECT GROUP_CONCAT(m.numero ORDER BY m.numero SEPARATOR ',') "
            "     FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa "
            "    WHERE pm.id_pedido = p.id_pedido) AS mesas "
            "FROM pedido p "
            "WHERE p.estado = 'PENDIENTE' "
            "  AND EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.id_pedido = p.id_pedido) "
            "ORDER BY p.fecha_creacion, p.id_pedido"
        )
        pedidos = cur.fetchall()

        cur.execute(
            "SELECT d.id_pedido, pr.nombre AS producto, d.cantidad, d.notas "
            "FROM detalle_pedido d "
            "JOIN pedido p ON p.id_pedido = d.id_pedido "
            "JOIN producto pr ON pr.id_producto = d.id_producto "
            "WHERE p.estado = 'PENDIENTE' "
            "ORDER BY p.fecha_creacion, p.id_pedido, d.id_detalle"
        )
        detalle = cur.fetchall()

        for p in pedidos:
            p["detalle"] = [
                {k: v for k, v in d.items() if k != "id_pedido"}
                for d in detalle
                if d["id_pedido"] == p["id_pedido"]
            ]
        return pedidos
    finally:
        cur.close()
        conn.close()


@router.put("/{id_pedido}/en-preparacion")
def iniciar_preparacion(id_pedido: int, datos: CambioEstado):
    """HU-07: PENDIENTE -> EN_PREPARACION."""
    return cambiar_estado(id_pedido, datos.id_usuario, "EN_PREPARACION")


@router.put("/{id_pedido}/listo")
def marcar_listo(id_pedido: int, datos: CambioEstado):
    """HU-08: EN_PREPARACION -> LISTO."""
    return cambiar_estado(id_pedido, datos.id_usuario, "LISTO")
