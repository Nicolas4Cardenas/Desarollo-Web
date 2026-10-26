"""Interfaz de consola: HU-06, 07, 08 (cocina), HU-13, 14 (reportes) y HU-15 (historial).

Solo pide datos y muestra resultados: toda la lógica vive en servicio.py.
Cada opción indica el rol que necesita ([COCINA], [ADMIN], [MESERO]); con la opción 19 se cambia de usuario.
"""
from decimal import Decimal

import servicio
from errores import ErrorNegocio, SIN_CAMBIO


# ------------------------------------------------------------------ utilidades
def pesos(valor):
    return "$ " + f"{Decimal(valor):,.0f}".replace(",", ".")


def fecha(valor):
    return valor.strftime("%Y-%m-%d %H:%M:%S") if hasattr(valor, "strftime") else str(valor)


def minutos(valor):
    return "-" if valor is None else f"{float(valor):.2f}"


def pedir_entero(mensaje):
    while True:
        dato = input(mensaje).strip()
        if dato.isdigit() and int(dato) > 0:
            return int(dato)
        print("  Escriba un número entero mayor que cero.")


def pedir_entero_opcional(mensaje):
    while True:
        dato = input(mensaje).strip()
        if dato == "":
            return None
        if dato.isdigit() and int(dato) > 0:
            return int(dato)
        print("  Escriba un número entero mayor que cero (o Enter para omitir).")


def pedir_texto(mensaje):
    return input(mensaje).strip()


def mostrar_cola(pedidos, titulo):
    if not pedidos:
        print(f"\n  {titulo}: no hay pedidos.\n")
        return
    print(f"\n  {titulo} ({len(pedidos)})")
    for p in pedidos:
        print(f"\n  Pedido #{p['id_pedido']}  |  Mesa(s): {', '.join(str(m) for m in p['mesas']) or '-'}  |  "
              f"Creado: {fecha(p['fecha_creacion'])}")
        for d in p["productos"]:
            print(f"     {d['cantidad']} x {d['producto']}" + (f"   ({d['notas']})" if d["notas"] else ""))
    print()


def mostrar_historial(registros):
    if not registros:
        print("  No hay registros de historial.\n")
        return
    print(f"\n  {'ID':>4}  {'Pedido':>6}  {'Estado':<15}{'Fecha':<21}Usuario")
    for h in registros:
        print(f"  {h['id_historial']:>4}  {h['id_pedido']:>6}  {h['estado']:<15}{fecha(h['fecha']):<21}"
              f"{h['usuario']} ({h['rol']})")
    print()


def mostrar_pedido(p):
    print(f"\n  Pedido #{p['id_pedido']}  |  Estado: {p['estado']}  |  "
          f"Mesa(s): {', '.join(str(m) for m in p['mesas']) or '-'}  |  Mesero: {p['mesero']}")
    print(f"  Creado: {fecha(p['fecha_creacion'])}   Última actualización: {fecha(p['fecha_ultima_actualizacion'])}")
    for d in p["productos"]:
        print(f"  {d['id_detalle']:>4}  {d['producto']:<22}{d['cantidad']:>5}{pesos(d['precio_unitario']):>12}"
              f"{pesos(d['subtotal']):>12}  {d['notas'] or ''}")
    print(f"  TOTAL: {pesos(p['total'])}\n")


# --------------------------------------------------------------------- apoyo
def ver_menu(u):
    categoria = None
    print()
    for f in servicio.listar_menu(u["id_usuario"]):
        if f["categoria"] != categoria:
            categoria = f["categoria"]
            print(f"  -- {categoria} --")
        print(f"  [{f['id_producto']:>2}] {f['nombre']:<22}{pesos(f['precio']):>10}   {f['descripcion'] or ''}")
    print()


def ver_mesas(u):
    mesas = servicio.listar_mesas_libres(u["id_usuario"])
    print("\n  Mesas libres: " + (", ".join(f"{m['numero']} (id {m['id_mesa']})" for m in mesas) or "ninguna") + "\n")


def crear_pedido(u):
    ver_mesas(u)
    id_pedido = servicio.crear_pedido(u["id_usuario"], pedir_entero("  Id de la mesa para el pedido: "))
    print(f"[OK] Pedido #{id_pedido} creado en estado PENDIENTE.")


def agregar_producto(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    ver_menu(u)
    id_producto = pedir_entero("  Id del producto: ")
    cantidad = pedir_entero("  Cantidad: ")
    notas = pedir_texto("  Notas (Enter = ninguna): ")
    r = servicio.agregar_producto(u["id_usuario"], id_pedido, id_producto, cantidad, notas or None)
    print(f"[OK] Producto agregado. Total del pedido: {pesos(r['total'])}")


def entregar(u):
    servicio.marcar_entregado(u["id_usuario"], pedir_entero("  Id del pedido a marcar como entregado: "))
    print("[OK] Pedido marcado como ENTREGADO.")


def cancelar(u):
    servicio.cancelar_pedido(u["id_usuario"], pedir_entero("  Id del pedido a cancelar: "))
    print("[OK] Pedido CANCELADO.")


def listar_pedidos(u):
    estado = pedir_texto("  Filtrar por estado (Enter = todos): ").upper() or None
    pedidos = servicio.listar_pedidos(u["id_usuario"], estado)
    print(f"\n  {'#':>4}  {'Estado':<15}{'Mesa(s)':<10}{'Total':>12}  Creado")
    for p in pedidos:
        print(f"  {p['id_pedido']:>4}  {p['estado']:<15}{','.join(str(m) for m in p['mesas']):<10}"
              f"{pesos(p['total']):>12}  {fecha(p['fecha_creacion'])}")
    print()


def ver_pedido(u):
    mostrar_pedido(servicio.obtener_pedido(u["id_usuario"], pedir_entero("  Id del pedido: ")))


# ---------------------------------------------------------- HU-06 / 07 / 08
def hu06_cola(u):
    mostrar_cola(servicio.ver_cola(u["id_usuario"]), "COLA DE PEDIDOS PENDIENTES")


def hu07_ver(u):
    mostrar_cola(servicio.ver_en_preparacion(u["id_usuario"]), "PEDIDOS EN PREPARACIÓN")


def hu07_preparar(u):
    servicio.iniciar_preparacion(u["id_usuario"], pedir_entero("  Id del pedido a preparar: "))
    print("[OK] Pedido EN_PREPARACION.")


def hu08_listo(u):
    servicio.marcar_listo(u["id_usuario"], pedir_entero("  Id del pedido que ya está listo: "))
    print("[OK] Pedido marcado como LISTO.")


# ------------------------------------------------------------- HU-13 / 14
def _pedir_fecha(mensaje):
    return pedir_texto(mensaje)


def hu13_ventas(u):
    desde = _pedir_fecha("  Desde (AAAA-MM-DD): ")
    hasta = _pedir_fecha("  Hasta (AAAA-MM-DD): ")
    id_categoria = pedir_entero_opcional("  Id de categoría (Enter = todas): ")
    id_producto = pedir_entero_opcional("  Id de producto (Enter = todos): ")
    r = servicio.reporte_ventas(u["id_usuario"], desde, hasta, id_categoria, id_producto)
    t = r["resumen"]
    print(f"\n  REPORTE DE VENTAS  {desde} a {hasta}")
    print(f"  Pedidos entregados: {t['pedidos_entregados']}   Productos vendidos: {t['productos_vendidos']}   "
          f"Total: {pesos(t['total_ventas'])}")
    print("\n  Por categoría:")
    for c in r["por_categoria"]:
        print(f"    {c['categoria']:<18}{c['productos_vendidos']:>5} u.{pesos(c['total_ventas']):>14}")
    print("\n  Por producto:")
    for p in r["por_producto"]:
        print(f"    {p['producto']:<22}{p['categoria']:<16}{p['unidades_vendidas']:>5} u.{pesos(p['total_ventas']):>14}")
    print()


def hu14_tiempos(u):
    desde = _pedir_fecha("  Desde (AAAA-MM-DD): ")
    hasta = _pedir_fecha("  Hasta (AAAA-MM-DD): ")
    r = servicio.reporte_tiempos(u["id_usuario"], desde, hasta)
    print(f"\n  REPORTE DE TIEMPOS (minutos)  {desde} a {hasta}")
    print(f"  {'Pedido':>6}  {'En cola':>8}{'Prepar.':>9}{'Entrega':>9}{'Total':>9}")
    for f in r["detalle"]:
        print(f"  {f['id_pedido']:>6}  {minutos(f['min_espera_en_cola']):>8}{minutos(f['min_preparacion']):>9}"
              f"{minutos(f['min_espera_entrega']):>9}{minutos(f['min_total']):>9}")
    p = r["promedios"]
    print(f"\n  Pedidos preparados: {p['pedidos_preparados']}")
    print(f"  Promedios -> cola: {minutos(p['prom_min_espera_en_cola'])}  preparación: {minutos(p['prom_min_preparacion'])}  "
          f"entrega: {minutos(p['prom_min_espera_entrega'])}  total: {minutos(p['prom_min_total'])}\n")


# --------------------------------------------------------- HU-15 historial
def hu15_listar(u):
    mostrar_historial(servicio.listar_historial(u["id_usuario"], pedir_entero_opcional("  Id del pedido (Enter = todos): ")))


def hu15_ver(u):
    mostrar_historial([servicio.obtener_historial(u["id_usuario"], pedir_entero("  Id del registro de historial: "))])


def hu15_crear(u):
    id_pedido = pedir_entero("  Id del pedido: ")
    estado = pedir_texto("  Estado (PENDIENTE, EN_PREPARACION, LISTO, ENTREGADO, CANCELADO): ")
    f = pedir_texto("  Fecha y hora AAAA-MM-DD HH:MM:SS (Enter = ahora): ")
    autor = pedir_entero_opcional("  Id del usuario que hizo el cambio (Enter = yo): ")
    nuevo = servicio.crear_historial(u["id_usuario"], id_pedido, estado, f or None, autor)
    print(f"[OK] Registro de historial #{nuevo} creado.")


def hu15_editar(u):
    id_historial = pedir_entero("  Id del registro a editar: ")
    mostrar_historial([servicio.obtener_historial(u["id_usuario"], id_historial)])
    estado = pedir_texto("  Nuevo estado (Enter = conservar): ")
    f = pedir_texto("  Nueva fecha AAAA-MM-DD HH:MM:SS (Enter = conservar): ")
    autor = pedir_entero_opcional("  Nuevo id de usuario (Enter = conservar): ")
    servicio.editar_historial(u["id_usuario"], id_historial,
                              estado or SIN_CAMBIO, f or SIN_CAMBIO, SIN_CAMBIO if autor is None else autor)
    print("[OK] Registro de historial actualizado.")


def hu15_eliminar(u):
    id_historial = pedir_entero("  Id del registro a eliminar: ")
    mostrar_historial([servicio.obtener_historial(u["id_usuario"], id_historial)])
    if pedir_texto("  ¿Seguro que desea eliminarlo? (s/n): ").lower() != "s":
        print("  Operación cancelada.")
        return
    servicio.eliminar_historial(u["id_usuario"], id_historial)
    print("[OK] Registro de historial eliminado.")


OPCIONES = {
    "1": ("[MESERO] Ver menú disponible", ver_menu),
    "2": ("[MESERO] Ver mesas libres", ver_mesas),
    "3": ("[MESERO] Crear pedido (apoyo HU-01)", crear_pedido),
    "4": ("[MESERO] Agregar producto a un pedido (apoyo HU-02)", agregar_producto),
    "5": ("[MESERO] Marcar pedido entregado (apoyo HU-04)", entregar),
    "6": ("[MESERO] Cancelar pedido (apoyo HU-05)", cancelar),
    "7": ("[ADMIN]  Listar todos los pedidos", listar_pedidos),
    "8": ("[ADMIN]  Ver un pedido con sus productos", ver_pedido),
    "9": ("[COCINA] HU-06  Ver cola de pedidos pendientes", hu06_cola),
    "10": ("[COCINA] HU-07  Ver pedidos en preparación", hu07_ver),
    "11": ("[COCINA] HU-07  Iniciar preparación de un pedido", hu07_preparar),
    "12": ("[COCINA] HU-08  Marcar pedido como listo", hu08_listo),
    "13": ("[ADMIN]  HU-13  Reporte de ventas", hu13_ventas),
    "14": ("[ADMIN]  HU-14  Reporte de tiempos", hu14_tiempos),
    "15": ("[ADMIN]  HU-15  Historial: listar (todo o por pedido)", hu15_listar),
    "16": ("[ADMIN]  HU-15  Historial: ver un registro", hu15_ver),
    "17": ("[ADMIN]  HU-15  Historial: CREAR registro", hu15_crear),
    "18": ("[ADMIN]  HU-15  Historial: EDITAR registro", hu15_editar),
    "19": ("[ADMIN]  HU-15  Historial: ELIMINAR registro", hu15_eliminar),
}
CAMBIAR = "20"


def ejecutar(usuario):
    """Devuelve 'cambiar' si el usuario pidió entrar con otro usuario; None si salió."""
    print(f"\nBienvenido, {usuario['nombre']} (rol {usuario['rol']}).")
    while True:
        print("-" * 66)
        for clave, (texto, _) in OPCIONES.items():
            print(f"  {clave:>2}) {texto}")
        print(f"  {CAMBIAR}) Cambiar de usuario")
        print("   0) Salir")
        opcion = input("Opción: ").strip()
        if opcion == "0":
            return None
        if opcion == CAMBIAR:
            return "cambiar"
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
