"""Inicio de sesión: el hash bcrypt viene de la BD y se compara aquí (RF-16)."""
import getpass
from dataclasses import dataclass
from typing import Optional

import bcrypt

from . import procedimientos as sp
from . import ui


@dataclass
class Sesion:
    id_usuario: int
    nombre: str
    rol: str


def generar_hash(clave: str) -> str:
    return bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("ascii")


def pedir_clave_nueva(msg: str = "Contraseña nueva") -> str:
    """Pide y confirma una contraseña; devuelve su hash bcrypt."""
    while True:
        c1 = getpass.getpass(f"{msg} (mín. 6 caracteres): ")
        if c1 == "":
            raise ui.Cancelado()
        if len(c1) < 6:
            ui.error("Debe tener al menos 6 caracteres.")
            continue
        if len(c1.encode("utf-8")) > 72:
            ui.error("bcrypt admite máximo 72 bytes.")
            continue
        if c1 != getpass.getpass("Repite la contraseña: "):
            ui.error("No coinciden. Intenta de nuevo.")
            continue
        return generar_hash(c1)


def iniciar_sesion(intentos: int = 3) -> Optional[Sesion]:
    for restante in range(intentos, 0, -1):
        login = ui.leer_texto("Usuario")
        clave = getpass.getpass("Contraseña: ")
        filas = sp.obtener_credenciales(login)
        if filas:
            fila = filas[0]
            try:
                if bcrypt.checkpw(clave.encode("utf-8"), fila["contrasena_hash"].encode("ascii")):
                    return Sesion(fila["id_usuario"], fila["nombre"], fila["rol"])
            except ValueError:
                pass
        ui.error("Usuario o contraseña incorrectos." + (f" Intentos restantes: {restante - 1}" if restante > 1 else ""))
    return None
