"""Punto de entrada portable de la API. El primer administrador se configura localmente."""

import argparse
from getpass import getpass
from poli.db import Base, RAIZ
from poli.errores import ErrorBase, ErrorNegocio, exigir
from poli.servicio import Restaurante


def main(argv=None):
    p = argparse.ArgumentParser(
        description="PoliRestaurante API REST con driver SQL para Postman"
    )
    p.add_argument("--motor", choices=("sqlite", "mysql"), default="sqlite")
    p.add_argument(
        "--base", help="Ruta de la base SQLite; por defecto datos/polirestaurante.db"
    )
    p.add_argument("--config", default=str(RAIZ / "config_mysql.json"))
    p.add_argument("--puerto", type=int, default=5000)
    p.add_argument(
        "--crear-admin",
        action="store_true",
        help="Crear dueño localmente, sin contraseñas predeterminadas",
    )
    p.add_argument(
        "--verificar", action="store_true", help="Verificar conexión y esquema y salir"
    )
    a = p.parse_args(argv)
    if a.motor == "mysql" and a.base:
        p.error("--base solo se usa con SQLite.")
    if not 1 <= a.puerto <= 65535:
        p.error("--puerto debe estar entre 1 y 65535.")
    try:
        base = (
            Base.mysql_desde_archivo(a.config)
            if a.motor == "mysql"
            else Base(ruta=a.base)
        )
        base.inicializar()
        s = Restaurante(base)
        if a.verificar:
            print("Conexión y esquema correctos. Motor:", base.motor)
            return 0
        if a.crear_admin:
            exigir(
                s.necesita_admin(),
                "Ya hay usuarios. Inicia sesión con tu administrador; no se sobrescribió nada.",
            )
            nombre, login = input("Nombre del dueño: "), input(
                "Login del administrador: "
            )
            clave = getpass("Contraseña (mínimo 10 caracteres): ")
            exigir(
                clave == getpass("Repite la contraseña: "),
                "Las contraseñas no coinciden.",
            )
            uid = s.crear_primer_admin(nombre, login, clave)
            print(
                "Administrador creado. ID:",
                uid,
                "\nAhora inicia la API sin --crear-admin.",
            )
            return 0
        if s.necesita_admin():
            print(
                "Primero ejecuta este mismo comando agregando --crear-admin. No hay usuario/contraseña por defecto."
            )
            return 1
        from poli.api import crear_app

        app = crear_app(base)
        print("API: http://127.0.0.1:" + str(a.puerto) + "/api/v1")
        print(
            "Motor:",
            base.motor,
            "| Base:",
            (
                str(base.ruta)
                if base.motor == "sqlite"
                else base.configuracion["database"]
            ),
        )
        print(
            "Deja esta terminal abierta. Ctrl+C detiene el servidor. El modo debug está desactivado."
        )
        app.run(host="127.0.0.1", port=a.puerto, debug=False, use_reloader=False)
        return 0
    except (ErrorBase, ErrorNegocio, OSError) as exc:
        print("[AVISO]", exc)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nSalida solicitada.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
