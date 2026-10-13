from api.db import conexion

def listar_usuarios():
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("SELECT id_usuario, nombre, usuario_login, activo, id_rol FROM usuario")
        return cursor.fetchall()

def obtener_usuario(id_usuario):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("SELECT id_usuario, nombre, usuario_login, activo, id_rol FROM usuario WHERE id_usuario = %s", (id_usuario,))
        return cursor.fetchone()

def crear_usuario(nombre, usuario_login, contrasena_hash, id_rol):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "INSERT INTO usuario (nombre, usuario_login, contrasena_hash, activo, id_rol) VALUES (%s, %s, %s, True, %s)",
            (nombre, usuario_login, contrasena_hash, id_rol)
        )
        return cursor.lastrowid

def actualizar_usuario(id_usuario, nombre, usuario_login, id_rol):
    with conexion() as con, con.cursor() as cursor:
        cursor.execute(
            "UPDATE usuario SET nombre = %s, usuario_login = %s, id_rol = %s WHERE id_usuario = %s",
            (nombre, usuario_login, id_rol, id_usuario)
        )
        return cursor.rowcount > 0

def eliminar_usuario(id_usuario):
    # En lugar de borrarlo, la buena práctica es desactivarlo para no dañar el historial
    with conexion() as con, con.cursor() as cursor:
        cursor.execute("UPDATE usuario SET activo = False WHERE id_usuario = %s", (id_usuario,))
        return cursor.rowcount > 0