"""Consola: entrada/salida. Las reglas y el SQL están en servicio.py y db.py."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import csv
import getpass
import json
from .db import RAIZ
from .errores import ErrorNegocio, ErrorBase
from . import validaciones as v


class Volver(Exception):
    pass


def pedir(mensaje, defecto=None):
    valor = input(mensaje + (f" [{defecto}]" if defecto is not None else "") + ": ").strip()
    if valor.lower() == "/cancelar":
        raise Volver()
    return str(defecto) if not valor and defecto is not None else valor


def entero(mensaje, defecto=None, opcional=False):
    while True:
        valor = pedir(mensaje, defecto)
        if opcional and not valor:
            return None
        try:
            return v.entero(int(valor), mensaje)
        except (ValueError, ErrorNegocio):
            print("Escribe un entero positivo; /cancelar para volver.")


def si(mensaje, defecto=True):
    while True:
        valor = pedir(mensaje + " (s/n)", "s" if defecto else "n").lower()
        if valor in ("s", "si"):
            return True
        if valor in ("n", "no"):
            return False
        print("Responde s o n.")


def password(nueva=False):
    while True:
        p = getpass.getpass(
            "Contraseña" + (" nueva/temporal" if nueva else "") + " (/cancelar para volver): "
        )
        if p == "/cancelar":
            raise Volver()
        if not nueva:
            return p
        try:
            v.clave(p)
        except ErrorNegocio as exc:
            print(exc)
            continue
        if p != getpass.getpass("Repite la contraseña: "):
            print("No coinciden.")
            continue
        return p


def fecha(valor):
    if not valor:
        return "-"
    try:
        return (
            datetime.fromisoformat(valor.replace("Z", "+00:00"))
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
    except ValueError:
        return str(valor)


def tabla(filas, columnas):
    if not filas:
        print("\n(Sin registros)")
        return
    ancho = {
        k: min(32, max(len(t), max(len(str(f.get(k, ""))) for f in filas))) for k, t in columnas
    }
    print("\n" + " | ".join(t.ljust(ancho[k]) for k, t in columnas))
    print("-" * min(150, sum(ancho.values()) + 3 * (len(columnas) - 1)))
    for f in filas:
        print(
            " | ".join(
                str(f.get(k, "")).replace("\n", " ")[: ancho[k]].ljust(ancho[k])
                for k, t in columnas
            )
        )
    print("Los textos largos se abrevian en la tabla; el detalle muestra su contenido completo.\n")


def mostrar_pedido(p):
    print(f"\nPEDIDO #{p['id']} | {p['estado']} | versión {p['version']}")
    print(
        f"Servicio: {p['tipo']} | Mesa: {p['mesa'] or '-'} | Responsable: {p['responsable']} | Cocina ID: {p['cocinero_id'] or '-'}"
    )
    print(f"Creación: {fecha(p['creado'])} | Última actualización: {fecha(p['actualizado'])}")
    for d in p["detalles"]:
        print(
            f"  Línea {d['id']}: {d['cantidad']} x {d['producto_nombre']} | {v.pesos(d['precio_centavos'])} c/u | Subtotal {v.pesos(d['precio_centavos']*d['cantidad'])}"
        )
        if d["notas"]:
            print("    Notas:", d["notas"])
    if not p["detalles"]:
        print("  Sin productos; cocina no puede iniciar todavía.")
    print("TOTAL:", v.pesos(p["total_centavos"]))
    if p["motivo_cancelacion"]:
        print("Motivo cancelación:", p["motivo_cancelacion"])
    print("Historial:")
    for h in p["historial"]:
        print(f"  {fecha(h['fecha'])} | {h['estado']} | {h['usuario']} | {h['motivo']}")


def limpiar_csv(valor):
    # Evita que una nota o nombre se interprete como fórmula en Excel.
    texto = str(valor if valor is not None else "")
    return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) else texto


class Menu:
    def __init__(self, servicio):
        self.s = servicio
        self.token = None
        self.pendiente = None

    def primer_admin(self):
        print("\nCONFIGURACIÓN INICIAL: crea al dueño/administrador. No se cargarán ejemplos.")
        print("El usuario y contraseña siguientes son del restaurante, no de MySQL.")
        while self.s.necesita_admin():
            try:
                nombre = pedir("Nombre completo")
                login = pedir("Usuario del administrador")
                uid = self.s.crear_primer_admin(nombre, login, password(True))
                print(f"Administrador creado con ID {uid}. Ya puedes iniciar sesión.")
            except ErrorNegocio as exc:
                print("[AVISO]", exc)

    def ejecutar(self):
        self.primer_admin()
        while True:
            print("\nPOLIRESTAURANTE - BACKEND DRIVER\n1) Iniciar sesión\n0) Salir")
            opcion = pedir("Opción")
            if opcion == "0":
                return
            if opcion != "1":
                print("Opción inválida.")
                continue
            try:
                login = pedir("Usuario")
                self.token = self.s.iniciar_sesion(login, password())
                self.pendiente = None
                u = self.s.perfil(self.token)
                if u["debe_cambiar"]:
                    print("Debes reemplazar la contraseña temporal antes de acceder a tu rol.")
                    self.cambiar_password()
                    continue
                self.menu_rol()
            except Volver:
                pass
            except (ErrorNegocio, ErrorBase) as exc:
                print("[AVISO]", exc)
            finally:
                if self.token:
                    try:
                        self.s.cerrar_sesion(self.token)
                    except ErrorBase:
                        pass
                self.token = None
                self.pendiente = None

    def cambiar_password(self):
        actual = password()
        nueva = password(True)
        self.s.cambiar_clave(self.token, actual, nueva)
        self.token = None
        print("Contraseña actualizada. Inicia sesión con la nueva.")

    def menu_rol(self):
        while self.token:
            u = self.s.perfil(self.token)
            print(f"\n{u['nombre']} | {u['rol']} | fechas visibles en zona local del equipo")
            opciones = {
                "1": ("Ver menú/productos", self.productos),
                "2": ("Ver mesas y su ocupación", self.mesas),
                "3": ("Consultar pedidos / cola de cocina", self.pedidos),
                "4": ("Detalle e historial de un pedido", self.detalle),
                "80": ("Cambiar mi contraseña", self.cambiar_password),
                "90": ("Reintentar última operación incierta", self.reintentar),
                "91": ("Consultar una clave de operación", self.consultar_operacion),
            }
            if u["rol"] in ("MESERO", "ADMINISTRADOR"):
                opciones.update(
                    {
                        "10": ("Crear pedido (HU-01)", self.crear_pedido),
                        "11": ("Agregar producto (HU-02)", self.agregar),
                        "12": ("Editar cantidad y notas (HU-03)", self.editar),
                        "13": ("Quitar producto (HU-03)", self.quitar),
                        "14": ("Marcar entregado (HU-04)", lambda: self.estado("ENTREGADO")),
                        "15": (
                            "Cancelar pedido con motivo (HU-05)",
                            lambda: self.estado("CANCELADO"),
                        ),
                    }
                )
            if u["rol"] in ("COCINA", "ADMINISTRADOR"):
                opciones.update(
                    {
                        "20": ("Iniciar preparación", lambda: self.estado("EN_PREPARACION")),
                        "21": ("Marcar pedido listo", lambda: self.estado("LISTO")),
                    }
                )
            if u["rol"] == "ADMINISTRADOR":
                opciones.update(
                    {
                        "30": ("Gestionar usuarios y roles", self.usuarios),
                        "31": ("Gestionar categorías", self.categorias),
                        "32": ("Gestionar productos", self.gestion_productos),
                        "33": ("Gestionar mesas", self.gestion_mesas),
                        "34": ("Reasignar responsable/cocina de un pedido", self.reasignar),
                        "40": ("Reporte de ventas", self.ventas),
                        "41": ("Reporte de tiempos de preparación", self.tiempos),
                        "42": ("Auditoría de acciones", self.auditoria),
                        "43": ("Ver tablas reales (sin credenciales)", self.tablas),
                        "44": ("Respaldar base SQLite", self.respaldo),
                    }
                )
            for key, (etiqueta, _) in opciones.items():
                print(f"{key:>2}) {etiqueta}")
            print(" 0) Cerrar sesión")
            key = pedir("Opción")
            if key == "0":
                return
            if key not in opciones:
                print("Opción no disponible para tu rol.")
                continue
            try:
                opciones[key][1]()
            except Volver:
                print("Acción cancelada. No se enviaron los datos pendientes.")
            except ErrorNegocio as exc:
                print(f"[{exc.codigo}] {exc}")
                if exc.codigo == "SESION":
                    return
            except ErrorBase as exc:
                print("[BASE]", exc)

    def operacion(self, callback):
        key = str(uuid4())
        print("Clave de operación:", key)
        self.pendiente = (key, callback)
        try:
            r = callback(key)
        except ErrorNegocio:
            self.pendiente = None
            raise
        except ErrorBase:
            print(
                "Si la respuesta fue incierta, usa 90 para repetir los mismos datos o 91 para consultar la clave."
            )
            raise
        self.pendiente = None
        self.resultado(r)

    def resultado(self, r):
        print("[OK]", r.get("mensaje", "Operación confirmada."))
        if "id" in r:
            print("ID:", r["id"])
        if "version" in r:
            print("Versión:", r["version"])
        if "total_centavos" in r:
            print("Total:", v.pesos(r["total_centavos"]))

    def reintentar(self):
        if not self.pendiente:
            print("No hay una operación incierta en esta sesión.")
            return
        key, callback = self.pendiente
        print("Reintentando con la MISMA clave:", key)
        r = callback(key)
        self.pendiente = None
        self.resultado(r)

    def consultar_operacion(self):
        r = self.s.consultar_operacion(self.token, pedir("Clave UUID de la operación"))
        print("Confirmada:", fecha(r["fecha"]))
        self.resultado(r["resultado"])

    def productos(self):
        admin = self.s.perfil(self.token)["rol"] == "ADMINISTRADOR"
        filas = self.s.productos(self.token, admin)
        for f in filas:
            f["precio"] = v.pesos(f["precio_centavos"])
        tabla(
            filas,
            [
                ("id", "ID"),
                ("nombre", "Producto"),
                ("categoria", "Categoría"),
                ("precio", "Precio"),
                ("disponible", "Disponible"),
                ("activo", "Activo"),
            ],
        )

    def mesas(self):
        filas = self.s.mesas(self.token, self.s.perfil(self.token)["rol"] == "ADMINISTRADOR")
        tabla(
            filas,
            [
                ("id", "ID"),
                ("numero", "Número"),
                ("capacidad", "Capacidad"),
                ("activa", "Activa"),
                ("estado", "Estado"),
                ("pedido_id", "Pedido"),
            ],
        )

    def pedidos(self):
        cocina = self.s.perfil(self.token)["rol"] == "COCINA"
        print("Estados:", ", ".join(v.ESTADOS))
        estado = pedir("Estado (Enter=todos)") or None
        if estado:
            estado = estado.upper().replace(" ", "_")
        abiertos = si("Mostrar solo abiertos", True) if estado is None else False
        pagina = 1
        while True:
            r = self.s.listar_pedidos(self.token, estado, abiertos, pagina)
            for f in r["items"]:
                f["total"] = v.pesos(f["total_centavos"])
            print("Cola FIFO (más antiguo primero)." if cocina else "Más reciente primero.")
            tabla(
                r["items"],
                [
                    ("id", "Pedido"),
                    ("estado", "Estado"),
                    ("mesa", "Mesa"),
                    ("responsable", "Responsable"),
                    ("cocinero", "Cocina"),
                    ("total", "Total"),
                    ("version", "Versión"),
                ],
            )
            if not r["hay_mas"] or not si("Siguiente página", False):
                break
            pagina += 1

    def elegir_pedido(self):
        pid = entero("ID del pedido")
        p = self.s.obtener_pedido(self.token, pid)
        mostrar_pedido(p)
        return p

    def detalle(self):
        mostrar_pedido(self.s.obtener_pedido(self.token, entero("ID del pedido")))

    def crear_pedido(self):
        tipo = "LLEVAR" if si("¿Es para llevar?", False) else "SALON"
        mid = None
        if tipo == "SALON":
            self.mesas()
            mid = entero("ID de mesa (no su número)")
        responsable = None
        if self.s.perfil(self.token)["rol"] == "ADMINISTRADOR":
            print(
                "Enter deja el pedido a tu nombre. Otro ID debe ser un mesero o administrador activo."
            )
            responsable = entero("ID responsable (opcional)", opcional=True)
        if si("Confirmar creación"):
            self.operacion(lambda key: self.s.crear_pedido(self.token, tipo, mid, responsable, key))

    def agregar(self):
        p = self.elegir_pedido()
        self.productos()
        producto = entero("ID producto")
        cantidad = entero("Cantidad")
        notas = pedir("Notas (Enter=sin notas)")
        if si("Agregar esta línea"):
            self.operacion(
                lambda key: self.s.agregar_producto(
                    self.token, p["id"], producto, cantidad, notas, p["version"], key
                )
            )

    def editar(self):
        p = self.elegir_pedido()
        did = entero("ID de la línea")
        d = next((x for x in p["detalles"] if x["id"] == did), None)
        if not d:
            raise ErrorNegocio("NO_EXISTE", "La línea no pertenece al pedido.")
        cantidad = entero("Cantidad", d["cantidad"])
        notas = pedir("Notas (Enter=conservar; - = borrar)", d["notas"])
        notas = "" if notas == "-" else notas
        if si("Guardar modificación"):
            self.operacion(
                lambda key: self.s.editar_detalle(
                    self.token, p["id"], did, cantidad, notas, p["version"], key
                )
            )

    def quitar(self):
        p = self.elegir_pedido()
        did = entero("ID de línea a quitar")
        if si("Quitar la línea", False):
            self.operacion(
                lambda key: self.s.quitar_detalle(self.token, p["id"], did, p["version"], key)
            )

    def estado(self, nuevo):
        p = self.elegir_pedido()
        motivo = pedir("Motivo de cancelación") if nuevo == "CANCELADO" else ""
        if si("Confirmar " + nuevo, False):
            self.operacion(
                lambda key: self.s.cambiar_estado(
                    self.token, p["id"], nuevo, p["version"], motivo, key
                )
            )

    def reasignar(self):
        p = self.elegir_pedido()
        self.mostrar_usuarios()
        responsable = entero("Nuevo ID responsable (Enter=conservar)", opcional=True)
        cocinero = entero("Nuevo ID cocina (Enter=conservar)", opcional=True)
        motivo = pedir("Motivo de reasignación")
        if si("Confirmar reasignación", False):
            self.operacion(
                lambda key: self.s.reasignar_pedido(
                    self.token, p["id"], responsable, cocinero, p["version"], motivo, key
                )
            )

    def mostrar_usuarios(self):
        filas = self.s.listar_usuarios(self.token)
        tabla(
            filas,
            [
                ("id", "ID"),
                ("nombre", "Nombre"),
                ("login", "Usuario"),
                ("rol", "Rol"),
                ("activo", "Activo"),
                ("debe_cambiar", "Clave temporal"),
            ],
        )
        return filas

    def usuarios(self):
        filas = self.mostrar_usuarios()
        op = pedir("1=crear, 2=editar/restablecer, 3=desactivar, Enter=volver")
        if op not in ("1", "2", "3"):
            return
        uid = None
        u = {}
        if op != "1":
            uid = entero("ID usuario")
            u = next((x for x in filas if x["id"] == uid), None)
            if not u:
                raise ErrorNegocio("NO_EXISTE", "Usuario no encontrado.")
        if op == "3":
            if si("Desactivar acceso (conserva historia)", False):
                self.resultado(self.s.desactivar_usuario(self.token, uid))
            return
        nombre = pedir("Nombre", u.get("nombre"))
        login = pedir("Usuario", u.get("login"))
        rol = pedir("Rol: ADMINISTRADOR / MESERO / COCINA", u.get("rol", "MESERO")).upper()
        activo = si("Cuenta activa", bool(u.get("activo", True)))
        clave = (
            password(True) if op == "1" or si("Restablecer contraseña temporal", False) else None
        )
        if si("Guardar usuario"):
            self.resultado(
                self.s.guardar_usuario(self.token, nombre, login, rol, activo, clave, uid)
            )

    def categorias(self):
        filas = self.s.categorias(self.token)
        tabla(filas, [("id", "ID"), ("nombre", "Nombre")])
        op = pedir("1=crear, 2=editar, 3=eliminar vacía, Enter=volver")
        if op not in ("1", "2", "3"):
            return
        cid = entero("ID categoría") if op != "1" else None
        if op == "3":
            if si("Eliminar categoría vacía", False):
                self.resultado(self.s.eliminar_categoria(self.token, cid))
        else:
            nombre = pedir("Nombre de categoría")
            if si("Guardar categoría"):
                self.resultado(self.s.guardar_categoria(self.token, nombre, cid))

    def gestion_productos(self):
        self.productos()
        op = pedir("1=crear, 2=editar/reactivar, 3=archivar, Enter=volver")
        if op not in ("1", "2", "3"):
            return
        pid = None
        p = {}
        if op != "1":
            pid = entero("ID producto")
            p = next((x for x in self.s.productos(self.token, True) if x["id"] == pid), None)
            if not p:
                raise ErrorNegocio("NO_EXISTE", "Producto no encontrado.")
        if op == "3":
            if si("Archivar producto", False):
                self.resultado(self.s.archivar_producto(self.token, pid))
            return
        nombre = pedir("Nombre", p.get("nombre"))
        descripcion = pedir("Descripción", p.get("descripcion", ""))
        precio = pedir(
            "Precio COP (punto decimal, sin miles)",
            str(Decimal(p["precio_centavos"]) / 100) if p else None,
        )
        tabla(self.s.categorias(self.token), [("id", "ID"), ("nombre", "Categoría")])
        categoria = entero("ID categoría", p.get("categoria_id"))
        disponible = si("Disponible", bool(p.get("disponible", True)))
        activo = si("Activo", bool(p.get("activo", True)))
        if si("Guardar producto"):
            self.resultado(
                self.s.guardar_producto(
                    self.token, nombre, descripcion, precio, categoria, disponible, activo, pid
                )
            )

    def gestion_mesas(self):
        self.mesas()
        op = pedir("1=crear, 2=editar/reactivar, 3=archivar, Enter=volver")
        if op not in ("1", "2", "3"):
            return
        mid = None
        m = {}
        if op != "1":
            mid = entero("ID mesa")
            m = next((x for x in self.s.mesas(self.token, True) if x["id"] == mid), None)
            if not m:
                raise ErrorNegocio("NO_EXISTE", "Mesa no encontrada.")
        if op == "3":
            if si("Archivar mesa", False):
                self.resultado(self.s.archivar_mesa(self.token, mid))
            return
        numero = entero("Número de mesa", m.get("numero"))
        capacidad = entero("Capacidad", m.get("capacidad", 4))
        activa = si("Activa", bool(m.get("activa", True)))
        if si("Guardar mesa"):
            self.resultado(self.s.guardar_mesa(self.token, numero, capacidad, activa, mid))

    def exportar(self, filas, nombre):
        if not filas or not si("Exportar estos resultados a CSV", False):
            return
        carpeta = RAIZ / "exportaciones"
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / (nombre + "_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".csv")
        campos = list(filas[0])
        with ruta.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows({k: limpiar_csv(v) for k, v in fila.items()} for fila in filas)
        print("Exportado:", ruta)

    def ventas(self):
        print("Periodo de entrega, fechas UTC inclusive. Máximo 366 días.")
        desde = pedir("Desde AAAA-MM-DD")
        hasta = pedir("Hasta AAAA-MM-DD")
        categoria = entero("ID categoría (Enter=todas)", opcional=True)
        producto = entero("ID producto (Enter=todos)", opcional=True)
        r = self.s.ventas(self.token, desde, hasta, categoria, producto)
        print(
            "Ventas:",
            v.pesos(r["total_centavos"]),
            "| Pedidos:",
            r["pedidos"],
            "| Unidades:",
            r["unidades"],
        )
        for f in r["items"]:
            f["total_cop"] = str(Decimal(f["total_centavos"]) / 100)
        tabla(
            r["items"],
            [
                ("producto", "Producto"),
                ("categoria", "Categoría"),
                ("unidades", "Unidades"),
                ("total_cop", "Total COP"),
            ],
        )
        self.exportar(r["items"], "ventas")

    def tiempos(self):
        print("Periodo en que quedaron listos, fechas UTC inclusive.")
        r = self.s.tiempos(self.token, pedir("Desde AAAA-MM-DD"), pedir("Hasta AAAA-MM-DD"))
        print(
            "Promedio:",
            (
                str(r["promedio_segundos"]) + " segundos"
                if r["promedio_segundos"] is not None
                else "sin datos completos"
            ),
        )
        tabla(
            r["items"],
            [
                ("id", "Pedido"),
                ("inicio", "Inicio UTC"),
                ("listo", "Listo UTC"),
                ("segundos", "Segundos"),
            ],
        )
        self.exportar(r["items"], "tiempos")

    def auditoria(self):
        pagina = 1
        while True:
            r = self.s.auditoria(self.token, pagina)
            tabla(
                r["items"],
                [
                    ("id", "ID"),
                    ("usuario", "Usuario"),
                    ("accion", "Acción"),
                    ("entidad", "Entidad"),
                    ("entidad_id", "ID entidad"),
                    ("descripcion", "Descripción"),
                    ("fecha", "UTC"),
                ],
            )
            self.exportar(r["items"], "auditoria")
            if not r["hay_mas"] or not si("Siguiente página", False):
                break
            pagina += 1

    def tablas(self):
        print(
            "Tablas: sistema, usuario, categoria, producto, mesa, pedido, ocupacion, detalle, historial, auditoria"
        )
        nombre = pedir("Tabla")
        pagina = 1
        while True:
            r = self.s.inspeccionar(self.token, nombre, pagina)
            if r["items"]:
                tabla(r["items"], [(k, k) for k in r["items"][0]])
            else:
                print("(Tabla vacía)")
            if not r["hay_mas"] or not si("Siguiente página", False):
                break
            pagina += 1

    def respaldo(self):
        destino = (
            RAIZ
            / "respaldos"
            / ("restaurante_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db")
        )
        if si("Crear copia completa de la base SQLite", False):
            r = self.s.respaldar(self.token, destino)
            print(r["mensaje"])
            print(r["ruta"])
