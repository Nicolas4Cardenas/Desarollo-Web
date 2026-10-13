from api.db import conexion

def listar_mesas():
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("SELECT id_mesa, numero, estado FROM mesa")
        return cursor.fetchall()

def obtener_mesa(id_mesa):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("SELECT id_mesa, numero, estado FROM mesa WHERE id_mesa = %s", (id_mesa,))
        return cursor.fetchone()

def crear_mesa(numero):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("INSERT INTO mesa (numero) VALUES (%s)", (numero,))
        return cursor.lastrowid

def actualizar_mesa(id_mesa, numero, estado):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("UPDATE mesa SET numero = %s, estado = %s WHERE id_mesa = %s", (numero, estado, id_mesa))
        return cursor.rowcount > 0

def eliminar_mesa(id_mesa):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("DELETE FROM mesa WHERE id_mesa = %s", (id_mesa,))
        return cursor.rowcount > 0