"""Consulta administrativa con proyecciones seguras, sin credenciales ni sesiones."""

from .base import limite_pagina, pagina_de

# Única fuente de identificadores SQL de la inspección. Nada viene libre del cliente.
TABLAS = {
    "usuario": ("id,nombre,login,rol,activo,debe_cambiar", "id"),
    "categoria": ("*", "id"),
    "producto": ("*", "id"),
    "mesa": ("*", "id"),
    "pedido": ("*", "id"),
    "ocupacion": ("*", "mesa_id"),
    "detalle": ("*", "id"),
    "historial": ("*", "id"),
    "auditoria": ("*", "id"),
    "sistema": ("*", "id"),
}


def inspeccionar_tabla(cursor, tabla, pagina):
    columnas, orden = TABLAS[tabla]
    filas = cursor.execute(
        f"SELECT {columnas} FROM {tabla} ORDER BY {orden} LIMIT ? OFFSET ?",
        limite_pagina(pagina),
    ).all()
    return pagina_de(filas, pagina)
