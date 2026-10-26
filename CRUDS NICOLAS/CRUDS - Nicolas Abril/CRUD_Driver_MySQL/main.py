"""Programa principal:  python main.py"""
import menu
import servicio


def iniciar_sesion():
    while True:
        login = input("Usuario (admin, cocina1, mesero1...)  [0 = salir]: ").strip()
        if login == "0":
            return None
        usuario = servicio.buscar_usuario(login)
        if usuario is None:
            print("  Usuario no encontrado o inactivo.\n")
        else:
            return usuario


def main():
    print("=" * 66)
    print("  POLIRESTAURANTE - CRUD de Nicolas  (" + servicio.TECNOLOGIA + ")")
    print("=" * 66)
    try:
        usuario = iniciar_sesion()
        while usuario is not None:
            if menu.ejecutar(usuario) != "cambiar":
                break
            usuario = iniciar_sesion()
    except (EOFError, KeyboardInterrupt):
        print()
    except Exception as e:  # conexión caída, contraseña incorrecta, etc.
        print(f"\nNo se pudo trabajar con la base de datos: {e}")
        print("Revise el archivo .env (usuario, contraseña, puerto) y que MySQL esté encendido.")
        return
    print("Hasta luego.")


if __name__ == "__main__":
    main()
