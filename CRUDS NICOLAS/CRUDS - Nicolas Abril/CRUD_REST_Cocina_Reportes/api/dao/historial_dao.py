"""CRUD de historial_estado (HU-15) a través de los procedimientos sp_admin_*_historial.

(En la base local de Nicolas se quitaron los triggers que bloqueaban UPDATE y DELETE.)
"""
from api.dao.comun import conjuntos, consumir
from api.db import conexion


def listar(id_admin, id_pedido=None):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_listar_historial(%s, %s)", (id_admin, id_pedido))
        return conjuntos(cur)[0]


def obtener(id_admin, id_historial):
    """Registro o None si no existe."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_ver_historial(%s, %s)", (id_admin, id_historial))
        filas = conjuntos(cur)[0]
        return filas[0] if filas else None


def crear(id_admin, id_pedido, estado, fecha, id_usuario_cambio):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_crear_historial(%s, %s, %s, %s, %s, @id_historial)",
                    (id_admin, id_pedido, estado, fecha, id_usuario_cambio))
        consumir(cur)
        cur.execute("SELECT @id_historial AS id_historial")
        return cur.fetchone()["id_historial"]


def editar(id_admin, id_historial, estado, fecha, id_usuario_cambio):
    """Los valores None conservan el dato actual."""
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_editar_historial(%s, %s, %s, %s, %s)",
                    (id_admin, id_historial, estado, fecha, id_usuario_cambio))
        consumir(cur)


def eliminar(id_admin, id_historial):
    with conexion() as con, con.cursor() as cur:
        cur.execute("CALL sp_admin_eliminar_historial(%s, %s)", (id_admin, id_historial))
        consumir(cur)
