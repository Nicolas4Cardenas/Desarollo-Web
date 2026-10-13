from api.db import conexion


def listar_categorias():
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "SELECT id_categoria, nombre FROM categoria"
        )
        return cursor.fetchall()


def obtener_categoria(id_categoria):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "SELECT id_categoria, nombre FROM categoria WHERE id_categoria = %s",
            (id_categoria,)
        )
        return cursor.fetchone()


def crear_categoria(nombre):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "INSERT INTO categoria (nombre) VALUES (%s)",
            (nombre,)
        )
        con.commit()
        return cursor.lastrowid


def actualizar_categoria(id_categoria, nombre):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "UPDATE categoria SET nombre = %s WHERE id_categoria = %s",
            (nombre, id_categoria)
        )
        con.commit()
        return cursor.rowcount > 0


def eliminar_categoria(id_categoria):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "DELETE FROM categoria WHERE id_categoria = %s",
            (id_categoria,)
        )
        con.commit()
        return cursor.rowcount > 0