"""Módulo MESERO (RF-01 .. RF-05)."""
from . import consultas as q
from . import procedimientos as sp
from . import ui, vistas
from .auth import Sesion


def ver_menu(s: Sesion) -> None:
    productos = q.menu_disponible()
    if not productos:
        ui.aviso("No hay productos disponibles.")
        return
    vistas.tabla_menu(productos)


def ver_mesas_libres(s: Sesion) -> None:
    mesas = q.mesas(estado="libre")
    if not mesas:
        ui.aviso("No hay mesas libres en este momento.")
        return
    vistas.tabla_mesas(mesas)


def _agregar_en_bucle(s: Sesion, id_pedido: int) -> None:
    productos = q.menu_disponible()
    if not productos:
        ui.aviso("No hay productos disponibles para agregar.")
        return
    vistas.tabla_menu(productos)
    validos = {p.id_producto: p for p in productos}
    while True:
        print()
        id_prod = ui.leer_entero("ID del producto a agregar (Enter para terminar)", minimo=1, opcional=True)
        if id_prod is None:
            break
        if id_prod not in validos:
            ui.error("Ese producto no está en el menú disponible.")
            continue
        cantidad = ui.leer_entero("Cantidad", minimo=1, defecto=1)
        notas = ui.leer_texto_opcional("Notas (Enter = sin notas)", maximo=255)

        def accion():
            total = sp.agregar_producto(s.id_usuario, id_pedido, id_prod, cantidad, notas)
            ui.ok(f"Agregado: {cantidad} x {validos[id_prod].nombre}. Total del pedido: {ui.dinero(total)}")

        ui.ejecutar(accion)


def crear_pedido(s: Sesion) -> None:
    mesas = q.mesas(estado="libre")
    if not mesas:
        ui.aviso("No hay mesas libres.")
        return
    vistas.tabla_mesas(mesas)
    por_numero = {m.numero: m for m in mesas}
    while True:
        numero = ui.leer_entero("Número de la mesa", minimo=1)
        if numero in por_numero:
            break
        ui.error("Esa mesa no está libre. Elige una de la lista.")
    id_pedido = sp.crear_pedido(s.id_usuario, por_numero[numero].id_mesa)
    ui.ok(f"Pedido #{id_pedido} creado para la mesa {numero} (PENDIENTE).")
    if ui.confirmar("¿Agregar productos ahora?", defecto=True):
        _agregar_en_bucle(s, id_pedido)


def _elegir_mio(s: Sesion, estados, vacio: str, msg: str = "ID del pedido"):
    pedido = vistas.elegir_pedido(q.pedidos(id_mesero=s.id_usuario, estados=estados), msg)
    if pedido is None:
        ui.aviso(vacio)
    return pedido


def agregar_producto(s: Sesion) -> None:
    p = _elegir_mio(s, ["PENDIENTE"], "No tienes pedidos PENDIENTES para editar.")
    if p:
        _agregar_en_bucle(s, p.id_pedido)


def modificar_detalle(s: Sesion) -> None:
    p = _elegir_mio(s, ["PENDIENTE"], "No tienes pedidos PENDIENTES para editar.")
    if not p:
        return
    print()
    vistas.mostrar_pedido(p)
    if not p.detalles:
        ui.aviso("Ese pedido aún no tiene productos.")
        return
    lineas = {d.id_detalle: d for d in p.detalles}
    while True:
        n = ui.leer_entero("ID de la línea a modificar", minimo=1)
        if n in lineas:
            break
        ui.error("Esa línea no existe en este pedido.")
    d = lineas[n]
    cantidad = ui.leer_entero("Nueva cantidad", minimo=1, defecto=d.cantidad)
    notas = ui.leer_texto_opcional("Notas", defecto=d.notas, maximo=255)
    total = sp.modificar_detalle(s.id_usuario, n, cantidad, notas)
    ui.ok(f"Línea actualizada. Total del pedido: {ui.dinero(total)}")


def quitar_producto(s: Sesion) -> None:
    p = _elegir_mio(s, ["PENDIENTE"], "No tienes pedidos PENDIENTES para editar.")
    if not p:
        return
    print()
    vistas.mostrar_pedido(p)
    if not p.detalles:
        ui.aviso("Ese pedido no tiene productos.")
        return
    lineas = {d.id_detalle: d for d in p.detalles}
    while True:
        n = ui.leer_entero("ID de la línea a quitar", minimo=1)
        if n in lineas:
            break
        ui.error("Esa línea no existe en este pedido.")
    if ui.confirmar(f"¿Quitar '{lineas[n].producto.nombre}' del pedido?"):
        total = sp.quitar_producto(s.id_usuario, n)
        ui.ok(f"Producto quitado. Total del pedido: {ui.dinero(total)}")


def mis_pedidos(s: Sesion) -> None:
    from .models import ESTADOS_PEDIDO
    print("Filtrar por estado (Enter = todos):")
    estado = ui.elegir("Estado", ESTADOS_PEDIDO, opcional=True)
    pedidos = q.pedidos(id_mesero=s.id_usuario, estados=[estado] if estado else None)
    if not pedidos:
        ui.aviso("No hay pedidos con ese filtro.")
        return
    vistas.tabla_pedidos(pedidos)


def ver_pedido(s: Sesion) -> None:
    p = _elegir_mio(s, None, "Aún no has creado pedidos.")
    if p:
        print()
        vistas.mostrar_pedido(p)


def pedidos_listos(s: Sesion) -> None:
    pedidos = q.pedidos(id_mesero=s.id_usuario, estados=["LISTO"])
    if not pedidos:
        ui.info("No tienes pedidos listos para recoger.")
        return
    ui.ok(f"Tienes {len(pedidos)} pedido(s) LISTO(S) para recoger en cocina:")
    vistas.tabla_pedidos(pedidos)


def marcar_entregado(s: Sesion) -> None:
    p = _elegir_mio(s, ["LISTO"], "No tienes pedidos LISTOS para entregar.", "ID del pedido entregado")
    if p and ui.confirmar(f"¿Marcar el pedido #{p.id_pedido} como ENTREGADO?", defecto=True):
        sp.marcar_entregado(s.id_usuario, p.id_pedido)
        ui.ok(f"Pedido #{p.id_pedido} entregado. La mesa quedó libre.")


def cancelar_pedido(s: Sesion) -> None:
    p = _elegir_mio(s, ["PENDIENTE", "EN_PREPARACION"], "No tienes pedidos que se puedan cancelar.",
                    "ID del pedido a cancelar")
    if p and ui.confirmar(f"¿Seguro que quieres CANCELAR el pedido #{p.id_pedido}?"):
        sp.cancelar_pedido(s.id_usuario, p.id_pedido)
        ui.ok(f"Pedido #{p.id_pedido} cancelado. La mesa quedó libre.")


def menu(s: Sesion) -> None:
    ui.menu(f"MESERO · {s.nombre}", [
        ("Ver menú disponible", lambda: ver_menu(s)),
        ("Ver mesas libres", lambda: ver_mesas_libres(s)),
        ("Crear pedido", lambda: crear_pedido(s)),
        ("Agregar productos a un pedido", lambda: agregar_producto(s)),
        ("Modificar cantidad/notas de un producto", lambda: modificar_detalle(s)),
        ("Quitar producto de un pedido", lambda: quitar_producto(s)),
        ("Mis pedidos", lambda: mis_pedidos(s)),
        ("Ver detalle de un pedido", lambda: ver_pedido(s)),
        ("Pedidos listos para recoger", lambda: pedidos_listos(s)),
        ("Marcar pedido como entregado", lambda: marcar_entregado(s)),
        ("Cancelar pedido", lambda: cancelar_pedido(s)),
    ], salida="Cerrar sesión")
