"""Módulo COCINA (RF-06 .. RF-08)."""
from . import consultas as q
from . import procedimientos as sp
from . import ui, vistas
from .auth import Sesion


def _mostrar_lista(pedidos, titulo_vacio: str) -> bool:
    if not pedidos:
        ui.info(titulo_vacio)
        return False
    for p in pedidos:
        print(ui.negrita(f"Pedido #{p.id_pedido}") + f"   Mesa(s): {p.mesas_txt}   "
              f"Desde: {ui.fecha_hora(p.fecha_creacion)}")
        ui.tabla(["Producto", "Cant.", "Notas"],
                 [[d.producto.nombre, d.cantidad, d.notas or ""] for d in p.detalles], derecha=[1])
        print()
    return True


def ver_cola(s: Sesion) -> None:
    _mostrar_lista(q.cola_pendientes(), "No hay pedidos pendientes. ¡Cocina al día!")


def ver_en_preparacion(s: Sesion) -> None:
    _mostrar_lista(q.en_preparacion(), "No hay pedidos en preparación.")


def iniciar_preparacion(s: Sesion) -> None:
    pedidos = q.cola_pendientes()
    if not pedidos:
        ui.info("No hay pedidos pendientes.")
        return
    p = vistas.elegir_pedido(pedidos, "ID del pedido a preparar (el más antiguo es el primero)")
    sp.iniciar_preparacion(s.id_usuario, p.id_pedido)
    ui.ok(f"Pedido #{p.id_pedido} ahora está EN PREPARACIÓN.")


def marcar_listo(s: Sesion) -> None:
    pedidos = q.en_preparacion()
    if not pedidos:
        ui.info("No hay pedidos en preparación.")
        return
    p = vistas.elegir_pedido(pedidos, "ID del pedido terminado")
    sp.marcar_listo(s.id_usuario, p.id_pedido)
    ui.ok(f"Pedido #{p.id_pedido} está LISTO. El mesero ya puede recogerlo.")


def menu(s: Sesion) -> None:
    ui.menu(f"COCINA · {s.nombre}", [
        ("Ver cola de pendientes (más antiguos primero)", lambda: ver_cola(s)),
        ("Ver pedidos en preparación", lambda: ver_en_preparacion(s)),
        ("Iniciar preparación de un pedido", lambda: iniciar_preparacion(s)),
        ("Marcar pedido como LISTO", lambda: marcar_listo(s)),
    ], salida="Cerrar sesión")
