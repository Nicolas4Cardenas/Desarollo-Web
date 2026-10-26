"""CRUD de cocina, reportes e historial con acceso DIRECTO A LAS TABLAS mediante el driver oficial
mysql-connector-python (sin ORM y sin procedimientos almacenados).

Aquí se escribe el SQL a mano (INSERT / SELECT / UPDATE / DELETE con parámetros %s) y las reglas
de negocio de HU-06, 07, 08, 13, 14 y 15 se aplican en Python:
  - cada operación abre una transacción: commit si todo sale bien, rollback si falla (RNF-10)
  - se bloquean las filas con SELECT ... FOR UPDATE para evitar choques entre usuarios
  - cada cambio de estado se registra en historial_estado (HU-15)
  - los roles se validan contra las tablas usuario / rol (COCINA, ADMINISTRADOR, MESERO);
    el ADMINISTRADOR puede ejecutar cualquier operación (también en pedidos de otros meseros)
"""
from contextlib import contextmanager
from decimal import Decimal

import mysql.connector

from config import Config
from errores import ErrorNegocio, SIN_CAMBIO
from validaciones import (limpiar_notas, validar_cantidad, validar_estado, validar_fecha_hora,
                          validar_rango)

TECNOLOGIA = "driver mysql-connector-python"
ACTIVOS = ("PENDIENTE", "EN_PREPARACION", "LISTO")
# Transiciones válidas del motor de estados (igual que sp_cambiar_estado del backend)
TRANSICIONES = {
    ("PENDIENTE", "EN_PREPARACION"), ("EN_PREPARACION", "LISTO"), ("LISTO", "ENTREGADO"),
    ("PENDIENTE", "CANCELADO"), ("EN_PREPARACION", "CANCELADO"),
}


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
    """Valida el rol contra las tablas usuario / rol. El ADMINISTRADOR puede hacer cualquier operación.
    Devuelve el rol real del usuario."""
    cur.execute(
        "SELECT r.nombre AS rol FROM usuario u JOIN rol r ON r.id_rol = u.id_rol "
        "WHERE u.id_usuario = %s AND u.activo = TRUE", (id_usuario,))
    fila = cur.fetchone()
    if fila is None or (fila["rol"] != rol and fila["rol"] != "ADMINISTRADOR"):
        raise ErrorNegocio("ACCESO_DENEGADO", "El usuario no tiene permiso para esta operación")
    return fila["rol"]


def _pedido_bloqueado(cur, id_pedido):
    """Pedido (FOR UPDATE) que debe existir."""
    cur.execute("SELECT id_pedido, estado, id_usuario_mesero FROM pedido WHERE id_pedido = %s FOR UPDATE",
                (id_pedido,))
    pedido = cur.fetchone()
    if pedido is None:
        raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
    return pedido


def _liberar_mesas(cur, id_pedido):
    """La mesa vuelve a 'libre' si no tiene otro pedido activo (HU-11)."""
    cur.execute(
        "UPDATE mesa m JOIN pedido_mesa pm ON pm.id_mesa = m.id_mesa AND pm.id_pedido = %s "
        "SET m.estado = 'libre' "
        "WHERE NOT EXISTS (SELECT 1 FROM pedido_mesa pm2 JOIN pedido p2 ON p2.id_pedido = pm2.id_pedido "
        "                  WHERE pm2.id_mesa = m.id_mesa AND pm2.id_pedido <> %s "
        "                    AND p2.estado IN ('PENDIENTE','EN_PREPARACION','LISTO'))",
        (id_pedido, id_pedido))


def _cambiar_estado(cur, pedido, nuevo, id_usuario):
    """Motor de estados: valida la transición, actualiza el pedido y registra el historial."""
    if (pedido["estado"], nuevo) not in TRANSICIONES:
        raise ErrorNegocio("TRANSICION_INVALIDA", "El cambio de estado no está permitido")
    cur.execute("UPDATE pedido SET estado = %s, fecha_ultima_actualizacion = NOW() WHERE id_pedido = %s",
                (nuevo, pedido["id_pedido"]))
    cur.execute("INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio) "
                "VALUES (%s, %s, NOW(), %s)", (pedido["id_pedido"], nuevo, id_usuario))
    if nuevo in ("ENTREGADO", "CANCELADO"):
        _liberar_mesas(cur, pedido["id_pedido"])


def _total(cur, id_pedido):
    cur.execute("SELECT COALESCE(SUM(cantidad * precio_unitario), 0) AS total "
                "FROM detalle_pedido WHERE id_pedido = %s", (id_pedido,))
    return cur.fetchone()["total"]


def _mesas_de(cur, id_pedido):
    cur.execute("SELECT m.numero FROM pedido_mesa pm JOIN mesa m ON m.id_mesa = pm.id_mesa "
                "WHERE pm.id_pedido = %s ORDER BY m.numero", (id_pedido,))
    return [f["numero"] for f in cur.fetchall()]


def _productos_de(cur, id_pedido):
    cur.execute("SELECT pr.nombre AS producto, d.cantidad, d.notas FROM detalle_pedido d "
                "JOIN producto pr ON pr.id_producto = d.id_producto "
                "WHERE d.id_pedido = %s ORDER BY d.id_detalle", (id_pedido,))
    return cur.fetchall()


# ------------------------------------------------------------------ usuarios
def buscar_usuario(login):
    with transaccion() as cur:
        cur.execute("SELECT u.id_usuario, u.nombre, r.nombre AS rol FROM usuario u "
                    "JOIN rol r ON r.id_rol = u.id_rol WHERE u.usuario_login = %s AND u.activo = TRUE",
                    (login,))
        return cur.fetchone()


# =========================================================== HU-06 / 07 / 08
def ver_cola(id_usuario):
    """HU-06: pedidos PENDIENTES con al menos un producto, del más antiguo al más reciente."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "COCINA")
        cur.execute("SELECT p.id_pedido, p.fecha_creacion FROM pedido p WHERE p.estado = 'PENDIENTE' "
                    "AND EXISTS (SELECT 1 FROM detalle_pedido d WHERE d.id_pedido = p.id_pedido) "
                    "ORDER BY p.fecha_creacion, p.id_pedido")
        pedidos = cur.fetchall()
        for p in pedidos:
            p["mesas"] = _mesas_de(cur, p["id_pedido"])
            p["productos"] = _productos_de(cur, p["id_pedido"])
        return pedidos


def ver_en_preparacion(id_usuario):
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "COCINA")
        cur.execute("SELECT p.id_pedido, p.fecha_creacion, p.fecha_ultima_actualizacion FROM pedido p "
                    "WHERE p.estado = 'EN_PREPARACION' ORDER BY p.fecha_ultima_actualizacion, p.id_pedido")
        pedidos = cur.fetchall()
        for p in pedidos:
            p["mesas"] = _mesas_de(cur, p["id_pedido"])
            p["productos"] = _productos_de(cur, p["id_pedido"])
        return pedidos


def iniciar_preparacion(id_usuario, id_pedido):
    """HU-07: PENDIENTE -> EN_PREPARACION (el pedido debe tener productos)."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "COCINA")
        pedido = _pedido_bloqueado(cur, id_pedido)
        cur.execute("SELECT COUNT(*) AS n FROM detalle_pedido WHERE id_pedido = %s", (id_pedido,))
        if cur.fetchone()["n"] == 0:
            raise ErrorNegocio("PEDIDO_VACIO", "El pedido no tiene productos")
        _cambiar_estado(cur, pedido, "EN_PREPARACION", id_usuario)


def marcar_listo(id_usuario, id_pedido):
    """HU-08: EN_PREPARACION -> LISTO."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "COCINA")
        pedido = _pedido_bloqueado(cur, id_pedido)
        _cambiar_estado(cur, pedido, "LISTO", id_usuario)


# ================================================================== HU-13
def _filas_ventas(cur, desde, hasta, id_categoria, id_producto):
    """Renglones vendidos de pedidos ENTREGADOS cuya fecha de entrega cae en el rango."""
    cur.execute(
        "SELECT p.id_pedido, pr.id_producto, pr.nombre AS producto, c.id_categoria, c.nombre AS categoria, "
        "       d.cantidad, d.cantidad * d.precio_unitario AS subtotal "
        "FROM pedido p "
        "JOIN historial_estado h ON h.id_pedido = p.id_pedido AND h.estado = 'ENTREGADO' "
        "JOIN detalle_pedido d ON d.id_pedido = p.id_pedido "
        "JOIN producto pr ON pr.id_producto = d.id_producto "
        "JOIN categoria c ON c.id_categoria = pr.id_categoria "
        "WHERE p.estado = 'ENTREGADO' AND h.fecha >= %s AND h.fecha < DATE_ADD(%s, INTERVAL 1 DAY) "
        "  AND (%s IS NULL OR c.id_categoria = %s) AND (%s IS NULL OR pr.id_producto = %s)",
        (desde, hasta, id_categoria, id_categoria, id_producto, id_producto))
    return cur.fetchall()


def reporte_ventas(id_usuario, desde, hasta, id_categoria=None, id_producto=None):
    desde, hasta = validar_rango(desde, hasta)
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        filas = _filas_ventas(cur, desde, hasta, id_categoria, id_producto)
    por_categoria, por_producto = {}, {}
    for f in filas:
        c = por_categoria.setdefault(f["id_categoria"], {"categoria": f["categoria"],
                                                         "productos_vendidos": 0, "total_ventas": Decimal(0)})
        c["productos_vendidos"] += f["cantidad"]
        c["total_ventas"] += f["subtotal"]
        p = por_producto.setdefault(f["id_producto"], {"producto": f["producto"], "categoria": f["categoria"],
                                                       "unidades_vendidas": 0, "total_ventas": Decimal(0)})
        p["unidades_vendidas"] += f["cantidad"]
        p["total_ventas"] += f["subtotal"]
    return {
        "resumen": {"pedidos_entregados": len({f["id_pedido"] for f in filas}),
                    "productos_vendidos": sum(f["cantidad"] for f in filas),
                    "total_ventas": sum((f["subtotal"] for f in filas), Decimal(0))},
        "por_categoria": sorted(por_categoria.values(), key=lambda x: x["total_ventas"], reverse=True),
        "por_producto": sorted(por_producto.values(), key=lambda x: x["total_ventas"], reverse=True),
    }


# ================================================================== HU-14
def _minutos(inicio, fin):
    if inicio is None or fin is None:
        return None
    return Decimal((fin - inicio).total_seconds()) / 60


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return round(sum(valores) / len(valores), 2) if valores else None


def reporte_tiempos(id_usuario, desde, hasta):
    """Tiempos calculados a partir de historial_estado (primer registro de cada estado)."""
    desde, hasta = validar_rango(desde, hasta)
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        cur.execute(
            "SELECT p.id_pedido, "
            "  MIN(CASE WHEN h.estado = 'PENDIENTE'      THEN h.fecha END) AS t_creado, "
            "  MIN(CASE WHEN h.estado = 'EN_PREPARACION' THEN h.fecha END) AS t_prep, "
            "  MIN(CASE WHEN h.estado = 'LISTO'          THEN h.fecha END) AS t_listo, "
            "  MIN(CASE WHEN h.estado = 'ENTREGADO'      THEN h.fecha END) AS t_entregado "
            "FROM pedido p JOIN historial_estado h ON h.id_pedido = p.id_pedido "
            "WHERE p.estado <> 'CANCELADO' AND p.fecha_creacion >= %s AND p.fecha_creacion < DATE_ADD(%s, INTERVAL 1 DAY) "
            "GROUP BY p.id_pedido ORDER BY t_creado, p.id_pedido", (desde, hasta))
        filas = cur.fetchall()
    for f in filas:
        f["min_espera_en_cola"] = _minutos(f["t_creado"], f["t_prep"])
        f["min_preparacion"] = _minutos(f["t_prep"], f["t_listo"])
        f["min_espera_entrega"] = _minutos(f["t_listo"], f["t_entregado"])
        f["min_total"] = _minutos(f["t_creado"], f["t_entregado"])
    return {
        "detalle": filas,
        "promedios": {
            "pedidos_preparados": sum(1 for f in filas if f["t_listo"] is not None),
            "prom_min_espera_en_cola": _promedio([f["min_espera_en_cola"] for f in filas]),
            "prom_min_preparacion": _promedio([f["min_preparacion"] for f in filas]),
            "prom_min_espera_entrega": _promedio([f["min_espera_entrega"] for f in filas]),
            "prom_min_total": _promedio([f["min_total"] for f in filas]),
        },
    }


# ================================================== HU-15 historial (CRUD)
_SELECT_HISTORIAL = ("SELECT h.id_historial, h.id_pedido, h.estado, h.fecha, h.id_usuario_cambio, "
                     "u.nombre AS usuario, r.nombre AS rol FROM historial_estado h "
                     "JOIN usuario u ON u.id_usuario = h.id_usuario_cambio JOIN rol r ON r.id_rol = u.id_rol ")


def _historial_o_error(cur, id_historial):
    cur.execute(_SELECT_HISTORIAL + "WHERE h.id_historial = %s", (id_historial,))
    fila = cur.fetchone()
    if fila is None:
        raise ErrorNegocio("HISTORIAL_NO_EXISTE", "El registro de historial no existe")
    return fila


def _exigir_usuario_existente(cur, id_usuario):
    cur.execute("SELECT 1 FROM usuario WHERE id_usuario = %s", (id_usuario,))
    if cur.fetchone() is None:
        raise ErrorNegocio("USUARIO_NO_EXISTE", "El usuario indicado no existe")


def listar_historial(id_usuario, id_pedido=None):
    """READ (lista): todo el historial o el de un pedido."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        sql, params = _SELECT_HISTORIAL, []
        if id_pedido is not None:
            sql += "WHERE h.id_pedido = %s "
            params.append(id_pedido)
        cur.execute(sql + "ORDER BY h.id_pedido, h.fecha, h.id_historial", params)
        return cur.fetchall()


def obtener_historial(id_usuario, id_historial):
    """READ (uno)."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        return _historial_o_error(cur, id_historial)


def crear_historial(id_usuario, id_pedido, estado, fecha=None, id_usuario_cambio=None):
    """CREATE: fecha (por defecto ahora) y usuario (por defecto quien lo crea) son opcionales."""
    estado = validar_estado(estado)
    fecha = validar_fecha_hora(fecha) if fecha is not None else None
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        cur.execute("SELECT 1 FROM pedido WHERE id_pedido = %s", (id_pedido,))
        if cur.fetchone() is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
        autor = id_usuario_cambio or id_usuario
        _exigir_usuario_existente(cur, autor)
        cur.execute("INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio) "
                    "VALUES (%s, %s, COALESCE(%s, NOW()), %s)", (id_pedido, estado, fecha, autor))
        return cur.lastrowid


def editar_historial(id_usuario, id_historial, estado=SIN_CAMBIO, fecha=SIN_CAMBIO, id_usuario_cambio=SIN_CAMBIO):
    """UPDATE: solo se modifican los campos enviados (los SIN_CAMBIO se conservan)."""
    if estado is SIN_CAMBIO and fecha is SIN_CAMBIO and id_usuario_cambio is SIN_CAMBIO:
        raise ErrorNegocio("CAMPO_REQUERIDO", "Indique al menos un dato para editar")
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        actual = _historial_o_error(cur, id_historial)
        nuevo_estado = actual["estado"] if estado is SIN_CAMBIO else validar_estado(estado)
        nueva_fecha = actual["fecha"] if fecha is SIN_CAMBIO else validar_fecha_hora(fecha)
        nuevo_autor = actual["id_usuario_cambio"] if id_usuario_cambio is SIN_CAMBIO else id_usuario_cambio
        _exigir_usuario_existente(cur, nuevo_autor)
        cur.execute("UPDATE historial_estado SET estado = %s, fecha = %s, id_usuario_cambio = %s "
                    "WHERE id_historial = %s", (nuevo_estado, nueva_fecha, nuevo_autor, id_historial))


def eliminar_historial(id_usuario, id_historial):
    """DELETE."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        _historial_o_error(cur, id_historial)
        cur.execute("DELETE FROM historial_estado WHERE id_historial = %s", (id_historial,))


# ============================================ apoyo (HU de mesero / admin)
_SELECT_PEDIDO = ("SELECT p.id_pedido, p.estado, p.fecha_creacion, p.fecha_ultima_actualizacion, "
                  "u.nombre AS mesero FROM pedido p JOIN usuario u ON u.id_usuario = p.id_usuario_mesero ")


def listar_menu(id_usuario):
    with transaccion() as cur:
        rol = _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute("SELECT c.nombre AS categoria, p.id_producto, p.nombre, p.descripcion, p.precio "
                    "FROM producto p JOIN categoria c ON c.id_categoria = p.id_categoria "
                    "WHERE p.disponibilidad = TRUE ORDER BY c.nombre, p.nombre")
        return cur.fetchall()


def listar_mesas_libres(id_usuario):
    with transaccion() as cur:
        rol = _exigir_rol(cur, id_usuario, "MESERO")
        cur.execute("SELECT id_mesa, numero FROM mesa WHERE estado = 'libre' ORDER BY numero")
        return cur.fetchall()


def crear_pedido(id_usuario, id_mesa):
    """HU-01 (apoyo)."""
    with transaccion() as cur:
        rol = _exigir_rol(cur, id_usuario, "MESERO")
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
        cur.execute("INSERT INTO historial_estado (id_pedido, estado, fecha, id_usuario_cambio) "
                    "VALUES (%s, 'PENDIENTE', NOW(), %s)", (id_pedido, id_usuario))
        return id_pedido


def agregar_producto(id_usuario, id_pedido, id_producto, cantidad, notas=None):
    """HU-02 (apoyo): un renglón por producto; si ya estaba, se suma la cantidad."""
    notas = limpiar_notas(notas)
    with transaccion() as cur:
        rol = _exigir_rol(cur, id_usuario, "MESERO")
        validar_cantidad(cantidad)
        pedido = _pedido_bloqueado(cur, id_pedido)
        if rol != "ADMINISTRADOR" and pedido["id_usuario_mesero"] != id_usuario:
            raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
        if pedido["estado"] != "PENDIENTE":
            raise ErrorNegocio("PEDIDO_BLOQUEADO", "Solo se puede editar un pedido en estado PENDIENTE")
        cur.execute("SELECT precio, disponibilidad FROM producto WHERE id_producto = %s", (id_producto,))
        producto = cur.fetchone()
        if producto is None:
            raise ErrorNegocio("PRODUCTO_NO_EXISTE", "El producto indicado no existe")
        if not producto["disponibilidad"]:
            raise ErrorNegocio("PRODUCTO_NO_DISPONIBLE", "El producto no está disponible")
        cur.execute("SELECT id_detalle FROM detalle_pedido WHERE id_pedido = %s AND id_producto = %s",
                    (id_pedido, id_producto))
        existente = cur.fetchone()
        if existente:
            id_detalle = existente["id_detalle"]
            cur.execute("UPDATE detalle_pedido SET cantidad = cantidad + %s, notas = COALESCE(%s, notas) "
                        "WHERE id_detalle = %s", (cantidad, notas, id_detalle))
        else:
            cur.execute("INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, notas, precio_unitario) "
                        "VALUES (%s, %s, %s, %s, %s)", (id_pedido, id_producto, cantidad, notas, producto["precio"]))
            id_detalle = cur.lastrowid
        cur.execute("UPDATE pedido SET fecha_ultima_actualizacion = NOW() WHERE id_pedido = %s", (id_pedido,))
        return {"id_detalle": id_detalle, "total": _total(cur, id_pedido)}


def marcar_entregado(id_usuario, id_pedido):
    """HU-04 (apoyo)."""
    with transaccion() as cur:
        rol = _exigir_rol(cur, id_usuario, "MESERO")
        pedido = _pedido_bloqueado(cur, id_pedido)
        if rol != "ADMINISTRADOR" and pedido["id_usuario_mesero"] != id_usuario:
            raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
        if pedido["estado"] != "LISTO":
            raise ErrorNegocio("TRANSICION_INVALIDA", "Solo se puede entregar un pedido en estado LISTO")
        _cambiar_estado(cur, pedido, "ENTREGADO", id_usuario)


def cancelar_pedido(id_usuario, id_pedido):
    """HU-05 (apoyo): desde PENDIENTE o EN_PREPARACION (igual que el backend del grupo)."""
    with transaccion() as cur:
        rol = _exigir_rol(cur, id_usuario, "MESERO")
        pedido = _pedido_bloqueado(cur, id_pedido)
        if rol != "ADMINISTRADOR" and pedido["id_usuario_mesero"] != id_usuario:
            raise ErrorNegocio("ACCESO_DENEGADO", "El pedido pertenece a otro mesero")
        if pedido["estado"] == "ENTREGADO":
            raise ErrorNegocio("CANCELACION_NO_PERMITIDA", "El pedido ya fue entregado")
        _cambiar_estado(cur, pedido, "CANCELADO", id_usuario)


def listar_pedidos(id_usuario, estado=None):
    """Todos los pedidos (administrador)."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        sql, params = _SELECT_PEDIDO, []
        if estado:
            sql += "WHERE p.estado = %s "
            params.append(validar_estado(estado))
        cur.execute(sql + "ORDER BY p.fecha_creacion DESC, p.id_pedido DESC", params)
        pedidos = cur.fetchall()
        for p in pedidos:
            p["mesas"] = _mesas_de(cur, p["id_pedido"])
            p["total"] = _total(cur, p["id_pedido"])
        return pedidos


def obtener_pedido(id_usuario, id_pedido):
    """Un pedido con sus productos (administrador)."""
    with transaccion() as cur:
        _exigir_rol(cur, id_usuario, "ADMINISTRADOR")
        cur.execute(_SELECT_PEDIDO + "WHERE p.id_pedido = %s", (id_pedido,))
        fila = cur.fetchone()
        if fila is None:
            raise ErrorNegocio("PEDIDO_NO_EXISTE", "El pedido indicado no existe")
        fila["mesas"] = _mesas_de(cur, id_pedido)
        fila["total"] = _total(cur, id_pedido)
        cur.execute("SELECT d.id_detalle, pr.nombre AS producto, d.cantidad, d.precio_unitario, "
                    "d.cantidad * d.precio_unitario AS subtotal, d.notas FROM detalle_pedido d "
                    "JOIN producto pr ON pr.id_producto = d.id_producto WHERE d.id_pedido = %s "
                    "ORDER BY d.id_detalle", (id_pedido,))
        fila["productos"] = cur.fetchall()
        return fila
