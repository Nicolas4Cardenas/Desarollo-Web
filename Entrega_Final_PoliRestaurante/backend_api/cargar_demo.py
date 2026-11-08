"""Carga explícita de cuentas y catálogo de clase sobre el esquema existente."""

import argparse
from poli.db import Base, RAIZ
from poli.demo import cargar_demo
from poli.errores import ErrorBase, ErrorNegocio


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Carga 1 dueño nuevo, 3 meseros, 3 cocineros y catálogo de clase"
    )
    p.add_argument("--motor", choices=("sqlite", "mysql"), default="sqlite")
    p.add_argument("--config", default=str(RAIZ / "config_mysql.json"))
    p.add_argument("--base", help="Archivo SQLite alternativo")
    p.add_argument(
        "--restablecer-claves-demo",
        action="store_true",
        help="Solo cuentas de esta carga: restablecer claves, desbloquear y revocar sus sesiones",
    )
    a = p.parse_args(argv)
    if a.motor == "mysql" and a.base:
        p.error("--base solo se usa con SQLite.")
    try:
        base = (
            Base.mysql_desde_archivo(a.config)
            if a.motor == "mysql"
            else Base(ruta=a.base)
        )
        base.inicializar()
        r = cargar_demo(base, a.restablecer_claves_demo)
        print(
            "Motor:",
            base.motor,
            "| Base:",
            base.configuracion["database"] if base.motor == "mysql" else base.ruta,
        )
        print(r["mensaje"])
        print(
            "Nuevos registros:", ", ".join(f"{k}={v}" for k, v in r["creados"].items())
        )
        print(
            "Credenciales: CREDENCIALES_DEMO.txt en la carpeta principal del paquete."
        )
        print(
            "Inicia con: python iniciar_api.py"
            + (" --motor mysql" if a.motor == "mysql" else "")
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
