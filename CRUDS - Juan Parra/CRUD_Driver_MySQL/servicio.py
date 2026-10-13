"""CRUD de pedidos con acceso DIRECTO A LAS TABLAS mediante el driver oficial
mysql-connector-python (sin ORM y sin procedimientos almacenados).

Aquí se escribe el SQL a mano (INSERT / SELECT / UPDATE / DELETE con parámetros %s)
y las reglas de negocio de HU-01 a HU-05 se aplican en Python:
  - cada operación abre una transacción: commit si todo sale bien, rollback si falla (RNF-10)
  - se bloquean las filas con SELECT ... FOR UPDATE para evitar choques entre meseros
  - cada cambio de estado se registra en historial_estado (HU-15)
"""
from contextlib import contextmanager

import mysql.connector

from config import Config
from errores import ErrorNegocio, SIN_CAMBIO
from validaciones import limpiar_notas, validar_cantidad

TECNOLOGIA = "driver mysql-connector-python"
ACTIVOS = ("PENDIENTE", "EN_PREPARACION", "LISTO")


# ------------------------------------------------------------------ conexión
@contextmanager
def transaccion():
    """Abre conexión + cursor. Hace COMMIT al salir bien y ROLLBACK si hay error."""
    con = mysql.connector.connect(
        host=Config.DB_HOST, port=Config.DB_PORT,
        user=Config.DB_USER, password=Config.DB_PASSWORD, database=Config.DB_NAME,
        charset="utf8mb4", collation="utf8mb4_unicode_ci",
        autocommit=False,
    )
    cur = con.cursor(dictionary=True, buffered=True)
    try:
        yield cur
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        cur.close()
        con.close()


# ------------------------------------------------------- reglas / auxiliares
def _exigir_rol(cur, id_usuario, rol):
    cur.execute(
        "SELECT r.nombre AS rol FROM usuario u JOIN rol r ON r.id_rol = u.id_rol "
        "WHERE u.id_usuario = %s AND u.activo = TRUE", (id_usuario,))
    fila = cur.fetchone()
    if fila is None or fila["rol"] != rol:
        raise ErrorNegocio("ACCESO_DENEGADO", "El usuario no tiene permiso para esta operación")


def _pedido_propio(cur, id_usuario, id_pedido):
    """Pedido bloqueado (FOR UPDATE) que debe existir y pertenecer al mesero."""
    cur.execute(
        "SELECT id_pedido, estado, id_usuario_mesero FROM pedido WHERE id_pedido = %s FOR UPDATE",
        (id_pedido,))
    pedido = cur.fetchone()
    if pedido is None:
        raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
    if pedido["id_usuario_mesero"] != id_usuario:
        raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
    return pedido


def _exigir_pendiente(pedido):
    if pedido["estado"] != "PENDIENTE":
        raise ErrorNegocio("PEDIDO_BLOQUEADO", "Solo se puede editar un pedido en estado PENDIENTE")


def _total(cur, id_pedido):
    cur.execute("SELECT COALESCE(SUM(cantidad * precio_unitario), 0) AS total "
                "FROM detalle_pedido WHERE id_pedido = %s", (id_pedido,))
    return cur.fetchone()["total"]


def _tocar(cur, id_pedido):
    cur.execute("UPDATE pedido SET fecha_ultima_actualizacion = NOW() WHERE id_pedido = %s", (id_pedido,))


def _registrar_historial(cur, id_pedido, estado, id_usuario):
    cur.execute("INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio) "
                "VALUES (%s, %s, NOW(), %s)", (id_pedido, estado, id_usuario))


def _liberar_mesas(cur, id_pedido):
    """La mesa vuelve a 'libre' si no tiene otro pedido activo (HU-11)."""
    cur.execute(
        "UPDATE mesa m JOIN pedido_mesa pm ON pm.id_mesa = m.id_mesa AND pm.id_pedido = %s "
        "SET m.estado = 'libre' "
        "WHERE NOT EXISTS (SELECT 1 FROM pedido_mesa pm2 JOIN pedido p2 ON p2.id_pedido = pm2.id_pedido "
        "                  WHERE pm2.id_mesa = m.id_mesa AND pm2.id_pedido <> %s "
        "                    AND p2.estado IN ('PENDIENTE','EN_PREPARACION','LISTO'))",
        (id_pedido, id_pedido))


def _cambiar_estado(cur, id_pedido, nuevo, id_usuario):
    cur.execute("UPDATE pedido SET estado = %s, fecha_ultima_actualizacion = NOW() WHERE id_pedido = %s",
                (nuevo, id_pedido))
    _registrar_historial(cur, id_pedido, nuevo, id_usuario)
    if nuevo in ("ENTREGADO", "CANCELADO"):
        _liberar_mesas(cur, id_pedido)


def _mesas_de(cur, id_pedido):
    cur.execute("SELECT m.numero FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa "
                "WHERE pm.id_pedido = %s ORDER BY m.numero", (id_pedido,))
    return [f["numero"] for f in cur.fetchall()]


def _resumen(cur, fila):
    fila["mesas"] = _mesas_de(cur, fila["id_pedido"])
    fila["total"] = _total(cur, fila["id_pedido"])
    return fila


_SELECT_PEDIDO = ("SELECT p.id_pedido, p.estado, p.fecha_creacion, p.fecha_ultima_actualizacion, "
                  "u.nombre AS mesero FROM pedido p JOIN usuario u ON u.id_usuario = p.id_usuario_mesero ")


# ------------------------------------------------------------ usuarios y menú
def buscar_usuario(login):
    with transaccion() as cur:
        cur.execute("SELECT u.id_usuario, u.nombre, r.nombre AS rol FROM usuario u "
                    "JOIN rol r ON r.id_rol = u.id_rol WHERE u.usuario_login = %s AND u.activo = TRUE",
                    (login,))
        return cur.fetchone()


def listar_menu(id_usuario):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute("SELECT c.nombre AS categoria, p.id_producto, p.nombre, p.descripcion, p.precio "
                    "FROM producto p JOIN categoria c ON c.id_categoria = p.id_categoria "
                    "WHERE p.disponibilidad = TRUE ORDER BY c.nombre, p.nombre")
        return cur.fetchall()


def listar_mesas_libres(id_usuario):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute("SELECT id_mesa, numero FROM mesa WHERE estado = 'libre' ORDER BY numero")
        return cur.fetchall()


# --------------------------------------------------------------- HU-01 CREATE
def crear_pedido(id_usuario, id_mesa):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute("SELECT estado FROM mesa WHERE id_mesa = %s FOR UPDATE", (id_mesa,))
        mesa = cur.fetchone()
        if mesa is None:
            raise ErrorNegocio("MESA_NO_EXISTE", "La mesa indicada no existe")
        if mesa["estado"] != "libre":
            raise ErrorNegocio("MESA_OCUPADA", "La mesa no está disponible")
        cur.execute("INSERT INTO pedido (id_usuario_mesero, estado, fecha_creacion, fecha_ultima_actualizacion) "
                    "VALUES (%s, 'PENDIENTE', NOW(), NOW())", (id_usuario,))
        id_pedido = cur.lastrowid
        cur.execute("INSERT INTO pedido_mesa (id_pedido, id_mesa) VALUES (%s, %s)", (id_pedido, id_mesa))
        cur.execute("UPDATE mesa SET estado = 'ocupada' WHERE id_mesa = %s", (id_mesa,))
        _registrar_historial(cur, id_pedido, "PENDIENTE", id_usuario)
        return id_pedido


# ------------------------------------------------------------ HU-02 CREATE
def agregar_producto(id_usuario, id_pedido, id_producto, cantidad, notas=None):
    notas = limpiar_notas(notas)
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        validar_cantidad(cantidad)
        pedido = _pedido_propio(cur, id_usuario, id_pedido)
        _exigir_pendiente(pedido)
        cur.execute("SELECT precio, disponibilidad FROM producto WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()
        if producto is None:
            raise ErrorNegocio("PRODUCTO_NO_EXISTE", "El producto indicado no existe")
        if not producto["disponibilidad"]:
            raise ErrorNegocio("PRODUCTO_NO_DISPONIBLE", "El producto no está disponible")

        cur.execute("SELECT id_detalle FROM detalle_pedido WHERE id_pedido = %s AND id_producto = %s",
                    (id_pedido, id_producto))
        existente = cur.fetchone()
        if existente:        # un renglón por producto: se suma la cantidad
            id_detalle = existente["id_detalle"]
            cur.execute("UPDATE detalle_pedido SET cantidad = cantidad + %s, notas = COALESCE(%s, notas) "
                        "WHERE id_detalle = %s", (cantidad, notas, id_detalle))
        else:
            cur.execute("INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, notas, precio_unitario) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (id_pedido, id_producto, cantidad, notas, producto["precio"]))
            id_detalle = cur.lastrowid
        _tocar(cur, id_pedido)
        return {"id_detalle": id_detalle, "total": _total(cur, id_pedido)}


# ------------------------------------------------------ HU-03 UPDATE / DELETE
def _detalle_del_pedido(cur, id_pedido, id_detalle):
    cur.execute("SELECT id_detalle, notas FROM detalle_pedido WHERE id_detalle = %s AND id_pedido = %s",
                (id_detalle, id_pedido))
    detalle = cur.fetchone()
    if detalle is None:
        raise ErrorNegocio("DETALLE_NO_EXISTE", "El producto indicado no hace parte de este pedido")
    return detalle


def modificar_detalle(id_usuario, id_pedido, id_detalle, cantidad, notas=SIN_CAMBIO):
    if notas is not SIN_CAMBIO:
        notas = limpiar_notas(notas)
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        validar_cantidad(cantidad)
        pedido = _pedido_propio(cur, id_usuario, id_pedido)
        detalle = _detalle_del_pedido(cur, id_pedido, id_detalle)
        _exigir_pendiente(pedido)
        if notas is SIN_CAMBIO:
            notas = detalle["notas"]
        cur.execute("UPDATE detalle_pedido SET cantidad = %s, notas = %s WHERE id_detalle = %s",
                    (cantidad, notas, id_detalle))
        _tocar(cur, id_pedido)
        return {"id_pedido": id_pedido, "total": _total(cur, id_pedido)}


def quitar_producto(id_usuario, id_pedido, id_detalle):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        pedido = _pedido_propio(cur, id_usuario, id_pedido)
        _detalle_del_pedido(cur, id_pedido, id_detalle)
        _exigir_pendiente(pedido)
        cur.execute("DELETE FROM detalle_pedido WHERE id_detalle = %s", (id_detalle,))
        _tocar(cur, id_pedido)
        return {"id_pedido": id_pedido, "total": _total(cur, id_pedido)}


# ------------------------------------------------------ HU-04 / HU-05 UPDATE
def marcar_entregado(id_usuario, id_pedido):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        pedido = _pedido_propio(cur, id_usuario, id_pedido)
        if pedido["estado"] != "LISTO":
            raise ErrorNegocio("TRANSICION_INVALIDA", "Solo se puede entregar un pedido en estado LISTO")
        _cambiar_estado(cur, id_pedido, "ENTREGADO", id_usuario)


def cancelar_pedido(id_usuario, id_pedido):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        pedido = _pedido_propio(cur, id_usuario, id_pedido)
        if pedido["estado"] == "ENTREGADO":
            raise ErrorNegocio("CANCELACION_NO_PERMITIDA", "El pedido ya fue entregado")
        if pedido["estado"] == "CANCELADO":
            raise ErrorNegocio("TRANSICION_INVALIDA", "El pedido ya está cancelado")
        _cambiar_estado(cur, id_pedido, "CANCELADO", id_usuario)


# ------------------------------------------------------------------- READ
def obtener_pedido(id_usuario, id_pedido):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute(_SELECT_PEDIDO + "WHERE p.id_pedido = %s AND p.id_usuario_mesero = %s",
                    (id_pedido, id_usuario))
        fila = cur.fetchone()
        if fila is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido no existe o no pertenece a este mesero")
        _resumen(cur, fila)
        cur.execute("SELECT d.id_detalle, pr.nombre AS producto, d.cantidad, d.precio_unitario, "
                    "d.cantidad * d.precio_unitario AS subtotal, d.notas "
                    "FROM detalle_pedido d JOIN producto pr ON pr.id_producto = d.id_producto "
                    "WHERE d.id_pedido = %s ORDER BY d.id_detalle", (id_pedido,))
        fila["productos"] = cur.fetchall()
        return fila


def listar_pedidos(id_usuario, estado=None):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        sql = _SELECT_PEDIDO + "WHERE p.id_usuario_mesero = %s"
        params = [id_usuario]
        if estado:
            sql += " AND p.estado = %s"
            params.append(estado)
        cur.execute(sql + " ORDER BY p.fecha_creacion DESC, p.id_pedido DESC", params)
        return [_resumen(cur, f) for f in cur.fetchall()]


def obtener_historial(id_usuario, id_pedido):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute("SELECT 1 FROM pedido WHERE id_pedido = %s AND id_usuario_mesero = %s", (id_pedido, id_usuario))
        if cur.fetchone() is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido no existe o no pertenece a este mesero")
        cur.execute("SELECT h.estado, h.fecha, u.nombre AS usuario, r.nombre AS rol "
                    "FROM historial_estado h JOIN usuario u ON u.id_usuario = h.id_usuario_cambio "
                    "JOIN rol r ON r.id_rol = u.id_rol WHERE h.id_pedido = %s "
                    "ORDER BY h.fecha, h.id_historial", (id_pedido,))
        return cur.fetchall()


# ------------------------------------------------- utilidad de demostración
def avanzar_cocina(id_usuario_cocina, id_pedido):
    """Simula a cocina (fuera del alcance de HU-01..05) para poder demostrar HU-04."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario_cocina, "COCINA")
        cur.execute("SELECT estado FROM pedido WHERE id_pedido = %s FOR UPDATE", (id_pedido,))
        pedido = cur.fetchone()
        if pedido is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
        siguiente = {"PENDIENTE": "EN_PREPARACION", "EN_PREPARACION": "LISTO"}.get(pedido["estado"])
        if siguiente is None:
            raise ErrorNegocio("TRANSICION_INVALIDA", f"Cocina no puede avanzar un pedido {pedido['estado']}")
        if siguiente == "EN_PREPARACION":
            cur.execute("SELECT COUNT(*) AS n FROM detalle_pedido WHERE id_pedido = %s", (id_pedido,))
            if cur.fetchone()["n"] == 0:
                raise ErrorNegocio("PEDIDO_SIN_PRODUCTOS", "No se puede preparar un pedido sin productos")
        _cambiar_estado(cur, id_pedido, siguiente, id_usuario_cocina)
        return siguiente
