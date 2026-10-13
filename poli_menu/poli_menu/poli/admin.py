"""Módulo ADMINISTRACIÓN (RF-09 .. RF-14)."""
from datetime import date
from typing import Optional

from . import auth
from . import consultas as q
from . import procedimientos as sp
from . import ui, vistas
from .auth import Sesion
from .models import ESTADOS_PEDIDO


# ------------------------------------------------------------------ helpers
def _elegir_id(items, attr_id: str, msg: str, etiqueta: str):
    por_id = {getattr(i, attr_id): i for i in items}
    while True:
        n = ui.leer_entero(msg, minimo=1)
        if n in por_id:
            return por_id[n]
        ui.error(f"Ese {etiqueta} no existe en la lista.")


def _elegir_categoria(msg: str, opcional: bool = False) -> Optional[int]:
    filas = q.categorias_con_conteo()
    if not filas:
        ui.aviso("No hay categorías. Crea una primero.")
        raise ui.Cancelado()
    vistas.tabla_categorias(filas)
    validos = {f[0] for f in filas}
    while True:
        n = ui.leer_entero(msg, minimo=1, opcional=opcional)
        if n is None or n in validos:
            return n
        ui.error("Esa categoría no existe.")


# --------------------------------------------------------------- categorías
def listar_categorias(s: Sesion) -> None:
    filas = q.categorias_con_conteo()
    vistas.tabla_categorias(filas) if filas else ui.aviso("No hay categorías.")


def crear_categoria(s: Sesion) -> None:
    nombre = ui.leer_texto("Nombre de la categoría", maximo=50)
    ui.ok(f"Categoría creada con ID {sp.crear_categoria(s.id_usuario, nombre)}.")


def editar_categoria(s: Sesion) -> None:
    filas = q.categorias_con_conteo()
    if not filas:
        ui.aviso("No hay categorías.")
        return
    vistas.tabla_categorias(filas)
    por_id = {f[0]: f for f in filas}
    while True:
        n = ui.leer_entero("ID de la categoría a editar", minimo=1)
        if n in por_id:
            break
        ui.error("Esa categoría no existe.")
    nombre = ui.leer_texto("Nuevo nombre", defecto=por_id[n][1], maximo=50)
    sp.editar_categoria(s.id_usuario, n, nombre)
    ui.ok("Categoría actualizada.")


def eliminar_categoria(s: Sesion) -> None:
    n = _elegir_categoria("ID de la categoría a eliminar")
    if ui.confirmar("¿Eliminar definitivamente esta categoría?"):
        sp.eliminar_categoria(s.id_usuario, n)
        ui.ok("Categoría eliminada.")


# ---------------------------------------------------------------- productos
def listar_productos(s: Sesion) -> None:
    productos = q.productos()
    vistas.tabla_productos(productos) if productos else ui.aviso("No hay productos.")


def crear_producto(s: Sesion) -> None:
    nombre = ui.leer_texto("Nombre del producto", maximo=100)
    descripcion = ui.leer_texto_opcional("Descripción (Enter = ninguna)", maximo=255)
    precio = ui.leer_decimal("Precio en pesos (ej: 12000)")
    id_cat = _elegir_categoria("ID de la categoría")
    disponible = ui.confirmar("¿Disponible para la venta?", defecto=True)
    nuevo = sp.crear_producto(s.id_usuario, nombre, descripcion, precio, id_cat, disponible)
    ui.ok(f"Producto creado con ID {nuevo}.")


def editar_producto(s: Sesion) -> None:
    productos = q.productos()
    if not productos:
        ui.aviso("No hay productos.")
        return
    vistas.tabla_productos(productos)
    p = _elegir_id(productos, "id_producto", "ID del producto a editar", "producto")
    nombre = ui.leer_texto("Nombre", defecto=p.nombre, maximo=100)
    descripcion = ui.leer_texto_opcional("Descripción", defecto=p.descripcion, maximo=255)
    precio = ui.leer_decimal("Precio en pesos", defecto=p.precio)
    print("Categoría actual:", p.categoria.nombre)
    cambiar = ui.confirmar("¿Cambiar de categoría?")
    id_cat = _elegir_categoria("ID de la nueva categoría") if cambiar else p.id_categoria
    disponible = ui.confirmar("¿Disponible para la venta?", defecto=p.disponibilidad)
    sp.editar_producto(s.id_usuario, p.id_producto, nombre, descripcion, precio, id_cat, disponible)
    ui.ok("Producto actualizado.")


def activar_producto(s: Sesion) -> None:
    productos = q.productos()
    if not productos:
        ui.aviso("No hay productos.")
        return
    vistas.tabla_productos(productos)
    p = _elegir_id(productos, "id_producto", "ID del producto", "producto")
    nuevo = not p.disponibilidad
    if ui.confirmar(f"'{p.nombre}' está {'DISPONIBLE' if p.disponibilidad else 'NO disponible'}. "
                    f"¿Marcarlo como {'disponible' if nuevo else 'NO disponible'}?", defecto=True):
        sp.activar_producto(s.id_usuario, p.id_producto, nuevo)
        ui.ok("Disponibilidad actualizada.")


def eliminar_producto(s: Sesion) -> None:
    productos = q.productos()
    if not productos:
        ui.aviso("No hay productos.")
        return
    vistas.tabla_productos(productos)
    p = _elegir_id(productos, "id_producto", "ID del producto a eliminar", "producto")
    if ui.confirmar(f"¿Eliminar definitivamente '{p.nombre}'?"):
        sp.eliminar_producto(s.id_usuario, p.id_producto)
        ui.ok("Producto eliminado.")


# -------------------------------------------------------------------- mesas
def listar_mesas(s: Sesion) -> None:
    mesas = q.mesas()
    vistas.tabla_mesas(mesas) if mesas else ui.aviso("No hay mesas.")


def crear_mesa(s: Sesion) -> None:
    numero = ui.leer_entero("Número de la nueva mesa", minimo=1)
    ui.ok(f"Mesa creada con ID {sp.crear_mesa(s.id_usuario, numero)}.")


def editar_mesa(s: Sesion) -> None:
    mesas = q.mesas()
    if not mesas:
        ui.aviso("No hay mesas.")
        return
    vistas.tabla_mesas(mesas)
    m = _elegir_id(mesas, "id_mesa", "ID de la mesa a editar", "ID de mesa")
    numero = ui.leer_entero("Nuevo número", minimo=1, defecto=m.numero)
    sp.editar_mesa(s.id_usuario, m.id_mesa, numero)
    ui.ok("Mesa actualizada.")


def cambiar_estado_mesa(s: Sesion) -> None:
    mesas = q.mesas()
    if not mesas:
        ui.aviso("No hay mesas.")
        return
    vistas.tabla_mesas(mesas)
    m = _elegir_id(mesas, "id_mesa", "ID de la mesa", "ID de mesa")
    estado = ui.elegir("Nuevo estado", ["libre", "ocupada"])
    sp.cambiar_estado_mesa(s.id_usuario, m.id_mesa, estado)
    ui.ok(f"Mesa {m.numero} ahora está {estado}.")


# ----------------------------------------------------------------- usuarios
def listar_usuarios(s: Sesion) -> None:
    vistas.tabla_usuarios(q.usuarios())


def crear_usuario(s: Sesion) -> None:
    nombre = ui.leer_texto("Nombre completo", maximo=100)
    login = ui.leer_texto("Nombre de usuario (login)", maximo=50)
    rol = ui.elegir("Rol", q.roles())
    hash_ = auth.pedir_clave_nueva("Contraseña")
    ui.ok(f"Usuario creado con ID {sp.crear_usuario(s.id_usuario, nombre, login, hash_, rol)}.")


def _elegir_usuario(msg: str):
    usuarios = q.usuarios()
    vistas.tabla_usuarios(usuarios)
    return _elegir_id(usuarios, "id_usuario", msg, "usuario")


def editar_usuario(s: Sesion) -> None:
    u = _elegir_usuario("ID del usuario a editar")
    nombre = ui.leer_texto("Nombre", defecto=u.nombre, maximo=100)
    roles = q.roles()
    print(f"Rol actual: {u.rol.nombre}")
    rol = ui.elegir("Nuevo rol (Enter = mantener)", roles, opcional=True) or u.rol.nombre
    sp.editar_usuario(s.id_usuario, u.id_usuario, nombre, rol)
    ui.ok("Usuario actualizado.")


def cambiar_contrasena(s: Sesion) -> None:
    u = _elegir_usuario("ID del usuario")
    sp.cambiar_contrasena(s.id_usuario, u.id_usuario, auth.pedir_clave_nueva())
    ui.ok(f"Contraseña de '{u.usuario_login}' actualizada.")


def activar_usuario(s: Sesion) -> None:
    u = _elegir_usuario("ID del usuario")
    nuevo = not u.activo
    if ui.confirmar(f"'{u.usuario_login}' está {'ACTIVO' if u.activo else 'INACTIVO'}. "
                    f"¿{'Activarlo' if nuevo else 'Desactivarlo'}?", defecto=True):
        sp.activar_usuario(s.id_usuario, u.id_usuario, nuevo)
        ui.ok("Estado del usuario actualizado.")


# ---------------------------------------------------------- pedidos/reportes
def consultar_pedidos(s: Sesion) -> None:
    print("Filtrar por estado (Enter = todos):")
    estado = ui.elegir("Estado", ESTADOS_PEDIDO, opcional=True)
    pedidos = q.pedidos(estados=[estado] if estado else None)
    if not pedidos:
        ui.aviso("No hay pedidos con ese filtro.")
        return
    vistas.tabla_pedidos(pedidos, con_mesero=True)
    if ui.confirmar("¿Ver el detalle de alguno?"):
        p = vistas.elegir_pedido(pedidos)
        print()
        vistas.mostrar_pedido(p)


def historial_pedido(s: Sesion) -> None:
    id_pedido = ui.leer_entero("ID del pedido", minimo=1)
    filas = sp.historial_pedido(s.id_usuario, id_pedido)
    if not filas:
        ui.aviso("Ese pedido no tiene historial (¿existe?).")
        return
    ui.tabla(["#", "Estado", "Fecha", "Usuario", "Rol"],
             [[f["id_historial"], f["estado"], ui.fecha_hora(f["fecha"]), f["usuario"], f["rol"]] for f in filas],
             derecha=[0])


def reporte_ventas(s: Sesion) -> None:
    hoy = date.today()
    ini = ui.leer_fecha("Fecha inicial (AAAA-MM-DD)", hoy.replace(day=1))
    fin = ui.leer_fecha("Fecha final (AAAA-MM-DD)", hoy)
    print("\nFiltro por categoría (Enter = todas):")
    id_cat = _elegir_categoria("ID de categoría", opcional=True)
    id_prod = None
    if ui.confirmar("¿Filtrar por un producto?"):
        productos = q.productos()
        vistas.tabla_productos(productos)
        id_prod = _elegir_id(productos, "id_producto", "ID del producto", "producto").id_producto

    rs = sp.reporte_ventas(s.id_usuario, ini, fin, id_cat, id_prod)
    tot = rs[0][0] if rs and rs[0] else {"pedidos_entregados": 0, "productos_vendidos": 0, "total_ventas": 0}
    print()
    ui.banner(f"VENTAS  {ini} → {fin}")
    print(f"Pedidos entregados: {ui.num(tot['pedidos_entregados'])}   "
          f"Productos vendidos: {ui.num(tot['productos_vendidos'])}   "
          + ui.negrita(f"Total: {ui.dinero(tot['total_ventas'])}"))
    if len(rs) > 1 and rs[1]:
        print("\nPor categoría:")
        ui.tabla(["Categoría", "Unidades", "Ventas"],
                 [[f["categoria"], ui.num(f["productos_vendidos"]), ui.dinero(f["total_ventas"])] for f in rs[1]],
                 derecha=[1, 2])
    if len(rs) > 2 and rs[2]:
        print("\nPor producto:")
        ui.tabla(["Producto", "Categoría", "Unidades", "Ventas"],
                 [[f["producto"], f["categoria"], ui.num(f["unidades_vendidas"]), ui.dinero(f["total_ventas"])]
                  for f in rs[2]], derecha=[2, 3])
    if not (len(rs) > 1 and rs[1]):
        ui.info("No hay ventas (pedidos ENTREGADOS) en ese rango.")


def reporte_tiempos(s: Sesion) -> None:
    hoy = date.today()
    ini = ui.leer_fecha("Fecha inicial (AAAA-MM-DD)", hoy.replace(day=1))
    fin = ui.leer_fecha("Fecha final (AAAA-MM-DD)", hoy)
    rs = sp.reporte_tiempos(s.id_usuario, ini, fin)
    print()
    ui.banner(f"TIEMPOS  {ini} → {fin}")
    if len(rs) > 0 and rs[0]:
        ui.tabla(["Pedido", "En cola (min)", "Preparación (min)", "Espera entrega (min)", "Total (min)"],
                 [[f["id_pedido"], ui.num(f["min_espera_en_cola"], 1), ui.num(f["min_preparacion"], 1),
                   ui.num(f["min_espera_entrega"], 1), ui.num(f["min_total"], 1)] for f in rs[0]],
                 derecha=[0, 1, 2, 3, 4])
    else:
        ui.info("No hay pedidos en ese rango.")
    if len(rs) > 1 and rs[1]:
        p = rs[1][0]
        print(f"\nPromedios ({p['pedidos_preparados']} pedidos preparados):")
        ui.tabla(["En cola", "Preparación", "Espera entrega", "Total"],
                 [[ui.num(p["prom_min_espera_en_cola"], 2), ui.num(p["prom_min_preparacion"], 2),
                   ui.num(p["prom_min_espera_entrega"], 2), ui.num(p["prom_min_total"], 2)]],
                 derecha=[0, 1, 2, 3])


# -------------------------------------------------------------------- menús
def _submenu(titulo: str, opciones) -> None:
    ui.menu(titulo, opciones, salida="Volver al menú de administración")


def menu(s: Sesion) -> None:
    ui.menu(f"ADMINISTRADOR · {s.nombre}", [
        ("Categorías", lambda: _submenu("CATEGORÍAS", [
            ("Listar", lambda: listar_categorias(s)), ("Crear", lambda: crear_categoria(s)),
            ("Editar", lambda: editar_categoria(s)), ("Eliminar", lambda: eliminar_categoria(s))])),
        ("Productos", lambda: _submenu("PRODUCTOS", [
            ("Listar", lambda: listar_productos(s)), ("Crear", lambda: crear_producto(s)),
            ("Editar", lambda: editar_producto(s)), ("Activar / desactivar", lambda: activar_producto(s)),
            ("Eliminar", lambda: eliminar_producto(s))])),
        ("Mesas", lambda: _submenu("MESAS", [
            ("Listar", lambda: listar_mesas(s)), ("Crear", lambda: crear_mesa(s)),
            ("Editar número", lambda: editar_mesa(s)), ("Cambiar estado", lambda: cambiar_estado_mesa(s))])),
        ("Usuarios", lambda: _submenu("USUARIOS", [
            ("Listar", lambda: listar_usuarios(s)), ("Crear", lambda: crear_usuario(s)),
            ("Editar nombre / rol", lambda: editar_usuario(s)),
            ("Cambiar contraseña", lambda: cambiar_contrasena(s)),
            ("Activar / desactivar", lambda: activar_usuario(s))])),
        ("Pedidos y reportes", lambda: _submenu("PEDIDOS Y REPORTES", [
            ("Consultar pedidos", lambda: consultar_pedidos(s)),
            ("Historial de estados de un pedido", lambda: historial_pedido(s)),
            ("Reporte de ventas", lambda: reporte_ventas(s)),
            ("Reporte de tiempos de preparación", lambda: reporte_tiempos(s))])),
    ], salida="Cerrar sesión")
