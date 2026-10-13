from api.db import conexion

def listar_productos():
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("SELECT id_producto, nombre, descripcion, precio, disponibilidad, id_categoria FROM producto")
        return cursor.fetchall()

def obtener_producto(id_producto):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("SELECT id_producto, nombre, descripcion, precio, disponibilidad, id_categoria FROM producto WHERE id_producto = %s", (id_producto,))
        return cursor.fetchone()

def crear_producto(nombre, descripcion, precio, disponibilidad, id_categoria):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "INSERT INTO producto (nombre, descripcion, precio, disponibilidad, id_categoria) VALUES (%s, %s, %s, %s, %s)",
            (nombre, descripcion, precio, disponibilidad, id_categoria)
        )
        return cursor.lastrowid

def actualizar_producto(id_producto, nombre, descripcion, precio, disponibilidad, id_categoria):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "UPDATE producto SET nombre = %s, descripcion = %s, precio = %s, disponibilidad = %s, id_categoria = %s WHERE id_producto = %s",
            (nombre, descripcion, precio, disponibilidad, id_categoria, id_producto)
        )
        return cursor.rowcount > 0

def eliminar_producto(id_producto):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("DELETE FROM producto WHERE id_producto = %s", (id_producto,))
        return cursor.rowcount > 0