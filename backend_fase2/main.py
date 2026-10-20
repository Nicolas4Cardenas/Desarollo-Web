"""Entrada: python main.py. No necesita Flask, pip, ORM ni MySQL en modo portable."""

import argparse
from pathlib import Path
import sys
from poli.db import Base, RAIZ
from poli.servicio import Restaurante
from poli.menu import Menu, Volver
from poli.errores import ErrorNegocio, ErrorBase


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Backend de consola PoliRestaurante con driver SQL."
    )
    parser.add_argument("--motor", choices=("sqlite", "mysql"), default="sqlite")
    parser.add_argument(
        "--base",
        help="Archivo SQLite opcional. Predeterminado: datos/polirestaurante.db junto al programa.",
    )
    parser.add_argument(
        "--config",
        default=str(RAIZ / "config_mysql.json"),
        help="Configuración para el modo MySQL.",
    )
    parser.add_argument(
        "--verificar",
        action="store_true",
        help="Comprueba el esquema existente y termina; no crea administrador.",
    )
    args = parser.parse_args(argv)
    try:
        if args.motor == "mysql" and args.base:
            parser.error("--base es únicamente para SQLite.")
        base = (
            Base.mysql_desde_archivo(args.config) if args.motor == "mysql" else Base(ruta=args.base)
        )
        print("Motor:", base.motor)
        if base.motor == "sqlite":
            print("Archivo REAL de datos:", base.ruta)
        else:
            print("Servidor/base:", base.configuracion["host"], base.configuracion["database"])
        if args.verificar:
            if base.motor == "sqlite" and not base.ruta.exists():
                print(
                    "La base no existe todavía. Ejecuta python main.py para la configuración inicial."
                )
                return 1
            base.verificar_esquema()
            print("Esquema versión 1 correcto.")
            return 0
        base.inicializar()
        print("Escribe /cancelar en cualquier dato para volver. Contraseñas ocultas al escribir.")
        Menu(Restaurante(base)).ejecutar()
        return 0
    except (KeyboardInterrupt, EOFError, Volver):
        print("\nSalida solicitada. Las transacciones incompletas se revierten.")
        return 0
    except (ErrorNegocio, ErrorBase, OSError) as exc:
        print("[AVISO]", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
