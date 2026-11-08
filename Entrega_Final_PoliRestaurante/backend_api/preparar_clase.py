"""Configuración opcional por terminal, sin claves predeterminadas ni pedidos de prueba."""

import argparse
from getpass import getpass
from poli.db import Base, RAIZ
from poli.servicio import Restaurante
from poli.datos_iniciales import cargar_catalogo
from poli.errores import ErrorBase, ErrorNegocio, exigir


def main():
    p = argparse.ArgumentParser(
        description="Crear catálogo y, opcionalmente, empleados para clase"
    )
    p.add_argument("--motor", choices=("sqlite", "mysql"), default="sqlite")
    p.add_argument("--base")
    p.add_argument("--config", default=str(RAIZ / "config_mysql.json"))
    a = p.parse_args()
    if a.motor == "mysql" and a.base:
        p.error("--base solo se usa con SQLite.")
    try:
        b = (
            Base.mysql_desde_archivo(a.config)
            if a.motor == "mysql"
            else Base(ruta=a.base)
        )
        b.inicializar()
        s = Restaurante(b)
        exigir(
            not s.necesita_admin(),
            "Crea primero al dueño con iniciar_api.py --crear-admin (y --motor mysql si corresponde).",
        )
        t = s.iniciar_sesion(
            input("Login del administrador del restaurante: "),
            getpass("Su contraseña: "),
        )
        exigir(
            s.perfil(t)["rol"] == "ADMINISTRADOR",
            "Necesitas una cuenta de administrador.",
        )
        print(cargar_catalogo(s, t)["mensaje"])
        for rol, ejemplo in [("MESERO", "juan.parra"), ("COCINA", "cocina")]:
            if input(f"¿Crear una cuenta {rol}? [s/N]: ").strip().lower() != "s":
                continue
            nombre = input("Nombre: ")
            login = input(f"Login (ejemplo {ejemplo}): ")
            clave = getpass("Contraseña temporal (mínimo 10 caracteres): ")
            exigir(
                clave == getpass("Repite la contraseña temporal: "),
                "Las contraseñas no coinciden.",
            )
            print(s.guardar_usuario(t, nombre, login, rol, password=clave)["mensaje"])
        s.cerrar_sesion(t)
        print(
            "Configuración terminada. Inicia la API y abre cliente_juan/cliente.html con Live Server."
        )
        return 0
    except (ErrorBase, ErrorNegocio, OSError) as e:
        print("[AVISO]", e)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nSalida solicitada.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
