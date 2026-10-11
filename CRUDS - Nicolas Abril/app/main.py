from fastapi import FastAPI
from app.db import get_connection
from app.routers import historial, cocina
from app.routers import historial, cocina, reportes

app = FastAPI(title="PoliRestaurante - API Nicolas")
app.include_router(historial.router)
app.include_router(cocina.router)
app.include_router(reportes.router)

@app.get("/salud")
def salud():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tablas = [fila[0] for fila in cur.fetchall()]
    cur.close()
    conn.close()
    return {"estado": "ok", "tablas": tablas}