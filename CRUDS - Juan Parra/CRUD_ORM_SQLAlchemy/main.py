"""Programa principal:  python main.py"""
import servicio
import menu


def iniciar_sesion():
    while True:
        login = input("Usuario (ej. mesero1)  [0 = salir]: ").strip()
        if login == "0":
            return None
        usuario = servicio.buscar_usuario(login)
        if usuario is None:
            print("  Usuario no encontrado o inactivo.\n")
        elif usuario["rol"] != "MESERO":
            print("  Este CRUD es del módulo mesero. Use un usuario MESERO (mesero1 o mesero2).\n")
        else:
            return usuario


def main():
    print("=" * 62)
    print("  POLIRESTAURANTE - CRUD de pedidos  (" + servicio.TECNOLOGIA + ")")
    print("=" * 62)
    try:
        usuario = iniciar_sesion()
        if usuario is not None:
            menu.ejecutar(usuario)
    except (EOFError, KeyboardInterrupt):
        print()
    except Exception as e:  # conexión caída, contraseña incorrecta, etc.
        print(f"\nNo se pudo trabajar con la base de datos: {e}")
        print("Revise el archivo .env (usuario, contraseña, puerto) y que MySQL esté encendido.")
        return
    print("Hasta luego.")


if __name__ == "__main__":
    main()
