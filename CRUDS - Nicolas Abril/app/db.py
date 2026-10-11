import os
import mysql.connector
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

CODIGOS_HTTP = {
    "ACCESO_DENEGADO": 403,
    "PEDIDO_NO_EXISTE": 404,
    "TRANSICION_INVALIDA": 409,
    "PEDIDO_VACIO": 409,
    "RANGO_INVALIDO": 400,
}


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "poli_restaurante"),
    )


def llamar_sp(nombre, argumentos):
    """Llama un procedimiento almacenado y devuelve una lista de resultados
    (cada resultado es una lista de diccionarios)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.callproc(nombre, argumentos)
        resultados = []
        for r in cur.stored_results():
            columnas = [c[0] for c in r.description]
            resultados.append([dict(zip(columnas, fila)) for fila in r.fetchall()])
        conn.commit()
        return resultados
    except mysql.connector.Error as e:
        conn.rollback()
        mensaje = e.msg or str(e)
        codigo = mensaje.split(":")[0].strip()
        raise HTTPException(status_code=CODIGOS_HTTP.get(codigo, 400), detail=mensaje)
    finally:
        cur.close()
        conn.close()