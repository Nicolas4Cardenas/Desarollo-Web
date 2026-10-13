"""Pantallas reutilizables (tablas de productos, pedidos, mesas...)."""
from typing import List, Optional

from . import ui
from .models import Pedido

_COLORES = {
    "PENDIENTE": ui.amarillo, "EN_PREPARACION": ui.cian, "LISTO": ui.verde,
    "ENTREGADO": ui.tenue, "CANCELADO": ui.rojo,
}


def estado(e: str) -> str:
    return _COLORES.get(e, str)(e)


def tabla_menu(productos) -> None:
    ui.tabla(["ID", "Categoría", "Producto", "Descripción", "Precio"],
             [[p.id_producto, p.categoria.nombre, p.nombre, ui.recortar(p.descripcion), ui.dinero(p.precio)]
              for p in productos], derecha=[0, 4])


def tabla_productos(productos) -> None:
    ui.tabla(["ID", "Categoría", "Producto", "Precio", "Disponible", "Descripción"],
             [[p.id_producto, p.categoria.nombre, p.nombre, ui.dinero(p.precio),
               ui.si_no(p.disponibilidad), ui.recortar(p.descripcion, 30)] for p in productos],
             derecha=[0, 3])


def tabla_mesas(mesas) -> None:
    ui.tabla(["ID", "Mesa Nº", "Estado"], [[m.id_mesa, m.numero, m.estado] for m in mesas], derecha=[0, 1])


def tabla_categorias(filas) -> None:
    ui.tabla(["ID", "Categoría", "Productos"], filas, derecha=[0, 2])


def tabla_usuarios(usuarios) -> None:
    ui.tabla(["ID", "Nombre", "Usuario", "Rol", "Activo"],
             [[u.id_usuario, u.nombre, u.usuario_login, u.rol.nombre, ui.si_no(u.activo)] for u in usuarios],
             derecha=[0])


def tabla_pedidos(pedidos: List[Pedido], con_mesero: bool = False) -> None:
    cols = ["ID", "Mesa(s)", "Estado", "Ítems", "Total", "Creado", "Actualizado"]
    if con_mesero:
        cols.insert(2, "Mesero")
    filas = []
    for p in pedidos:
        fila = [p.id_pedido, p.mesas_txt, p.estado, sum(d.cantidad for d in p.detalles),
                ui.dinero(p.total), ui.fecha_hora(p.fecha_creacion), ui.fecha_hora(p.fecha_ultima_actualizacion)]
        if con_mesero:
            fila.insert(2, p.mesero.nombre)
        filas.append(fila)
    ui.tabla(cols, filas, derecha=[0])


def mostrar_pedido(p: Pedido, con_precios: bool = True) -> None:
    print(ui.negrita(f"Pedido #{p.id_pedido}") + f"   Mesa(s): {p.mesas_txt}   Estado: {estado(p.estado)}")
    print(f"Mesero: {p.mesero.nombre}   Creado: {ui.fecha_hora(p.fecha_creacion)}   "
          f"Actualizado: {ui.fecha_hora(p.fecha_ultima_actualizacion)}")
    if not p.detalles:
        print(ui.tenue("(sin productos todavía)"))
    elif con_precios:
        ui.tabla(["Línea", "Producto", "Cant.", "Precio", "Subtotal", "Notas"],
                 [[d.id_detalle, d.producto.nombre, d.cantidad, ui.dinero(d.precio_unitario),
                   ui.dinero(d.subtotal), d.notas or ""] for d in p.detalles], derecha=[0, 2, 3, 4])
    else:
        ui.tabla(["Producto", "Cant.", "Notas"],
                 [[d.producto.nombre, d.cantidad, d.notas or ""] for d in p.detalles], derecha=[1])
    if con_precios:
        print(ui.negrita(f"TOTAL: {ui.dinero(p.total)}"))


def elegir_pedido(pedidos: List[Pedido], msg: str = "ID del pedido", con_mesero: bool = False) -> Optional[Pedido]:
    """Muestra la lista y pide un ID de ella. None si la lista está vacía."""
    if not pedidos:
        return None
    tabla_pedidos(pedidos, con_mesero=con_mesero)
    por_id = {p.id_pedido: p for p in pedidos}
    while True:
        n = ui.leer_entero(msg, minimo=1)
        if n in por_id:
            return por_id[n]
        ui.error("Ese ID no está en la lista de arriba.")
