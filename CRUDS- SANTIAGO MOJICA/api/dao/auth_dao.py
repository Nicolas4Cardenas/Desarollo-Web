from api.db import conexion

def obtener_usuario_por_login(usuario_login):
    with conexion() as con, con.cursor() as cursor:
        # Llamamos al procedimiento almacenado que ya creaste en tu BD
        cursor.execute("CALL sp_auth_obtener_credenciales(%s)", (usuario_login,))
        return cursor.fetchone()