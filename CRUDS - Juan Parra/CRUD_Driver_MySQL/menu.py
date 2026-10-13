"""Interfaz de consola del módulo mesero (HU-01 a HU-05).

Solo pide datos y muestra resultados: toda la lógica vive en servicio.py.
"""
from decimal import Decimal

import servicio
from errores import ErrorNegocio, SIN_CAMBIO


# ------------------------------------------------------------------ utilidades
def pesos(valor):
    return "$ " + f"{Decimal(valor):,.0f}".replace(",", ".")


def fecha(valor):
    return valor.strftime("%Y-%m-%d %H:%M:%S") if hasattr(valor, "strftime") else str(valor)


def pedir_entero(mensaje):
    while True:
        dato = input(mensaje).strip()
        if dato.isdigit() and int(dato) > 0:
            return int(dato)
        print("  Escriba un número entero mayor que cero.")


def pedir_texto(mensaje):
    return input(mensaje).strip()


def mostrar_pedido(p):
    print(f"\n  Pedido #{p['id_pedido']}  |  Estado: {p['estado']}  |  "
          f"Mesa(s): {', '.join(str(m) for m in p['mesas']) or '-'}  |  Mesero: {p['mesero']}")
    print(f"  Creado: {fecha(p['fecha_creacion'])}   Última actualización: {fecha(p['fecha_ultima_actualizacion'])}")
    if p["productos"]:
        print(f"  {'ID':>4}  {'Producto':<22}{'Cant':>5}{'P. unit.':>12}{'Subtotal':>12}  Notas")
        for d in p["productos"]:
            print(f"  {d['id_detalle']:>4}  {d['producto']:<22}{d['cantidad']:>5}"
                  f"{pesos(d['precio_unitario']):>12}{pesos(d['subtotal']):>12}  {d['notas'] or ''}")
    else:
        print("  (sin productos)")
    print(f"  TOTAL: {pesos(p['total'])}\n")


def mostrar_lista(pedidos):
    if not pedidos:
        print("  No hay pedidos.\n")
        return
    print(f"\n  {'#':>4}  {'Estado':<15}{'Mesa(s)':<10}{'Total':>12}  Creado")
    for p in pedidos:
        mesas = ",".join(str(m) for m in p["mesas"])
        print(f"  {p['id_pedido']:>4}  {p['estado']:<15}{mesas:<10}{pesos(p['total']):>12}  {fecha(p['fecha_creacion'])}")
    print()


# --------------------------------------------------------------------- acciones
def ver_menu(u):
    filas = servicio.listar_menu(u["id_usuario"])
    categoria = None
    print()
    for f in filas:
        if f["categoria"] != categoria:
            categoria = f["categoria"]
            print(f"  -- {categoria} --")
        print(f"  [{f['id_producto']:>2}] {f['nombre']:<22}{pesos(f['precio']):>10}   {f['descripcion'] or ''}")
    print()


def ver_mesas(u):
    mesas = servicio.listar_mesas_libres(u["id_usuario"])
    print("\n  Mesas libres: " + (", ".join(f"{m['numero']} (id {m['id_mesa']})" for m in mesas) or "ninguna") + "\n")


def hu01_crear(u):
    ver_mesas(u)
    id_mesa = pedir_entero("  Id de la mesa para el pedido: ")
    id_pedido = servicio.crear_pedido(u["id_usuario"], id_mesa)
    print(f"[OK] Pedido #{id_pedido} creado en estado PENDIENTE.")
    mostrar_pedido(servicio.obtener_pedido(u["id_usuario"], id_pedido))


def hu02_agregar(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    ver_menu(u)
    id_producto = pedir_entero("  Id del producto: ")
    cantidad = pedir_entero("  Cantidad: ")
    notas = pedir_texto("  Notas (Enter = ninguna, ej. sin cebolla): ")
    r = servicio.agregar_producto(u["id_usuario"], id_pedido, id_producto, cantidad, notas or None)
    print(f"[OK] Producto agregado. Total del pedido: {pesos(r['total'])}")


def hu03_editar(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    mostrar_pedido(servicio.obtener_pedido(u["id_usuario"], id_pedido))
    id_detalle = pedir_entero("  ID del renglón a editar (columna ID): ")
    cantidad = pedir_entero("  Nueva cantidad: ")
    notas = pedir_texto("  Nuevas notas (Enter = conservar, '-' = borrar): ")
    nuevas = SIN_CAMBIO if notas == "" else (None if notas == "-" else notas)
    r = servicio.modificar_detalle(u["id_usuario"], id_pedido, id_detalle, cantidad, nuevas)
    print(f"[OK] Producto actualizado. Total del pedido: {pesos(r['total'])}")


def hu03_quitar(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    mostrar_pedido(servicio.obtener_pedido(u["id_usuario"], id_pedido))
    id_detalle = pedir_entero("  ID del renglón a quitar (columna ID): ")
    r = servicio.quitar_producto(u["id_usuario"], id_pedido, id_detalle)
    print(f"[OK] Producto quitado. Total del pedido: {pesos(r['total'])}")


def hu04_entregar(u):
    id_pedido = pedir_entero("  Id del pedido a marcar como entregado: ")
    servicio.marcar_entregado(u["id_usuario"], id_pedido)
    print("[OK] Pedido marcado como ENTREGADO.")


def hu05_cancelar(u):
    id_pedido = pedir_entero("  Id del pedido a cancelar: ")
    if pedir_texto(f"  ¿Seguro que desea cancelar el pedido #{id_pedido}? (s/n): ").lower() != "s":
        print("  Operación cancelada.")
        return
    servicio.cancelar_pedido(u["id_usuario"], id_pedido)
    print("[OK] Pedido CANCELADO. Quedó registrado en el historial.")


def listar(u):
    estado = pedir_texto("  Filtrar por estado (Enter = todos): ").upper() or None
    mostrar_lista(servicio.listar_pedidos(u["id_usuario"], estado))


def detalle(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    mostrar_pedido(servicio.obtener_pedido(u["id_usuario"], id_pedido))


def historial(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    print(f"\n  Historial del pedido #{id_pedido}")
    for h in servicio.obtener_historial(u["id_usuario"], id_pedido):
        print(f"  {fecha(h['fecha'])}  {h['estado']:<15} por {h['usuario']} ({h['rol']})")
    print()


def demo_cocina(u):
    cocina = servicio.buscar_usuario("cocina1")
    if cocina is None:
        print("[ERROR] No existe el usuario 'cocina1' en la base de datos.")
        return
    id_pedido = pedir_entero("  Id del pedido que cocina va a avanzar: ")
    nuevo = servicio.avanzar_cocina(cocina["id_usuario"], id_pedido)
    print(f"[OK] Cocina (cocina1) movió el pedido a {nuevo}.")


OPCIONES = {
    "1": ("Ver menú disponible", ver_menu),
    "2": ("Ver mesas libres", ver_mesas),
    "3": ("HU-01  Crear pedido", hu01_crear),
    "4": ("HU-02  Agregar producto a un pedido", hu02_agregar),
    "5": ("HU-03  Editar cantidad/notas de un producto", hu03_editar),
    "6": ("HU-03  Quitar producto de un pedido", hu03_quitar),
    "7": ("HU-04  Marcar pedido como entregado", hu04_entregar),
    "8": ("HU-05  Cancelar pedido", hu05_cancelar),
    "9": ("Ver mis pedidos", listar),
    "10": ("Ver detalle de un pedido", detalle),
    "11": ("Ver historial de estados de un pedido", historial),
    "12": ("[DEMO] Cocina avanza un pedido (PENDIENTE>EN_PREPARACION>LISTO)", demo_cocina),
}


def ejecutar(usuario):
    print(f"\nBienvenido, {usuario['nombre']} (rol {usuario['rol']}).")
    while True:
        print("-" * 62)
        for clave, (texto, _) in OPCIONES.items():
            print(f"  {clave:>2}) {texto}")
        print("   0) Salir")
        opcion = input("Opción: ").strip()
        if opcion == "0":
            return
        if opcion not in OPCIONES:
            print("  Opción no válida.")
            continue
        try:
            OPCIONES[opcion][1](usuario)
        except ErrorNegocio as e:
            print(f"[ERROR] {e}")
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as e:
            print(f"[ERROR] Falla inesperada con la base de datos: {e}")
