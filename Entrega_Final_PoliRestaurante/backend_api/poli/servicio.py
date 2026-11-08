"""Reglas, permisos y transacciones del restaurante; los DAO ejecutan las consultas."""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import secrets
from uuid import UUID
from .errores import exigir, ErrorNegocio
from .seguridad import hash_clave, verificar_clave, huella_token
from . import validaciones as v
from .dao import (
    AuditoriaDAO, CategoriaDAO, DetalleDAO, HistorialDAO, MesaDAO, OcupacionDAO,
    OperacionDAO, PedidoDAO, ProductoDAO, ReporteDAO, SesionDAO, UsuarioDAO,
)
from .dao.inspeccion import TABLAS, inspeccionar_tabla
from .fechas import BOGOTA, ZONA_COLOMBIA, leer_instante_utc, rango_utc_colombia

TODOS = v.ROLES


def ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def despues(horas=0, minutos=0):
    return (
        datetime.now(timezone.utc) + timedelta(hours=horas, minutes=minutos)
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Restaurante:
    def __init__(self, base):
        self.base = base

    def necesita_admin(self):
        with self.base.transaccion() as c:
            return UsuarioDAO(c).contar() == 0

    def crear_primer_admin(self, nombre, login, password):
        nombre, login, password = (
            v.texto(nombre, "Nombre"),
            v.login(login),
            v.clave(password),
        )
        h = hash_clave(password)
        with self.base.transaccion(True) as c:
            usuarios = UsuarioDAO(c)
            exigir(
                usuarios.contar() == 0,
                "Ya hay usuarios. El primer administrador ya fue configurado.",
                "YA_CONFIGURADO",
            )
            uid = usuarios.crear(nombre, login, h, "ADMINISTRADOR")
            self._auditar(
                c,
                uid,
                "PRIMER_ADMIN",
                "usuario",
                uid,
                "Administrador inicial creado sin datos comerciales.",
            )
            return uid

    def iniciar_sesion(self, login, password):
        login = v.login(login)
        exigir(
            isinstance(password, str) and len(password) <= 128,
            "Credenciales incorrectas.",
            "CREDENCIALES",
        )
        error = None
        resultado = None
        with self.base.transaccion(True) as c:
            usuarios, sesiones = UsuarioDAO(c), SesionDAO(c)
            u = usuarios.buscar_login(login)
            # Ejecutar una derivación incluso para un usuario desconocido.
            if not u:
                hashlib.pbkdf2_hmac(
                    "sha256", password.encode(), b"usuario-ausente00", 310000
                )
                error = ErrorNegocio(
                    "CREDENCIALES", "Usuario o contraseña incorrectos."
                )
            elif u["bloqueado_hasta"] and u["bloqueado_hasta"] > ahora():
                error = ErrorNegocio(
                    "BLOQUEADO",
                    "Cuenta temporalmente bloqueada. Espera 15 minutos o solicita restablecimiento al administrador.",
                )
            elif not u["activo"] or not verificar_clave(password, u["password_hash"]):
                fallos = (
                    u["fallos"]
                    if not u["bloqueado_hasta"] or u["bloqueado_hasta"] > ahora()
                    else 0
                ) + 1
                bloqueo = despues(minutos=15) if fallos >= 5 else None
                usuarios.registrar_intentos(u["id"], fallos, bloqueo)
                error = ErrorNegocio(
                    "CREDENCIALES", "Usuario o contraseña incorrectos."
                )
            else:
                token = secrets.token_urlsafe(32)
                usuarios.registrar_intentos(u["id"])
                sesiones.purgar_vencidas(ahora())
                sesiones.crear(huella_token(token), u["id"], ahora(), despues(horas=8))
                self._auditar(
                    c,
                    u["id"],
                    "LOGIN",
                    "usuario",
                    u["id"],
                    "Ingreso con contraseña verificada.",
                )
                resultado = token
        # El contador de intentos debe confirmarse antes de devolver el error.
        if error:
            raise error
        return resultado

    def _actor(self, c, token, roles=TODOS, permite_cambio=False):
        exigir(
            isinstance(token, str) and 20 <= len(token) <= 200,
            "Debes iniciar sesión.",
            "SESION",
        )
        u = SesionDAO(c).buscar_actor(huella_token(token))
        exigir(
            u and u["activo"] and u["expira"] > ahora(),
            "La sesión expiró o fue revocada. Inicia sesión nuevamente.",
            "SESION",
        )
        exigir(u["rol"] in roles, "Tu rol no permite esta operación.", "PERMISO")
        exigir(
            permite_cambio or not u["debe_cambiar"],
            "Primero cambia tu contraseña temporal.",
            "CAMBIAR_CLAVE",
        )
        return u

    def perfil(self, token):
        with self.base.transaccion() as c:
            return self._actor(c, token, permite_cambio=True)

    def cerrar_sesion(self, token):
        with self.base.transaccion(True) as c:
            SesionDAO(c).revocar(huella_token(token))

    def cambiar_clave(self, token, actual, nueva):
        nueva = v.clave(nueva)
        with self.base.transaccion(True) as c:
            u = self._actor(c, token, permite_cambio=True)
            usuarios = UsuarioDAO(c)
            exigir(
                verificar_clave(actual, usuarios.obtener(u["id"])["password_hash"]),
                "La contraseña actual no coincide.",
            )
            exigir(actual != nueva, "La contraseña nueva debe ser diferente.")
            usuarios.cambiar_clave(u["id"], hash_clave(nueva))
            SesionDAO(c).revocar_usuario(u["id"])
            self._auditar(
                c,
                u["id"],
                "CAMBIAR_CLAVE",
                "usuario",
                u["id"],
                "Contraseña propia actualizada; sesiones revocadas.",
            )

    def _auditar(self, c, uid, accion, entidad, eid, descripcion):
        AuditoriaDAO(c).registrar(uid, accion, entidad, eid, ahora(), descripcion)

    def _ejecutar(
        self, token, accion, entidad, datos, funcion, roles=TODOS, clave=None
    ):
        if clave is not None:
            try:
                exigir(
                    str(UUID(clave)) == clave,
                    "Clave de operación: UUID minúscula inválida.",
                )
            except (ValueError, TypeError, AttributeError):
                raise ErrorNegocio(
                    "DATO_INVALIDO", "Clave de operación: UUID minúscula inválida."
                ) from None
        huella = hashlib.sha256(
            json.dumps([accion, datos], sort_keys=True, ensure_ascii=True).encode()
        ).hexdigest()
        with self.base.transaccion(True) as c:
            u = self._actor(c, token, roles)
            operaciones = OperacionDAO(c)
            if clave:
                anterior = operaciones.buscar(u["id"], clave)
                if anterior:
                    exigir(
                        anterior["huella"] == huella,
                        "La clave de operación pertenece a otra solicitud.",
                        "CONFLICTO",
                    )
                    return json.loads(anterior["resultado"])
            resultado = funcion(c, u)
            self._auditar(
                c,
                u["id"],
                accion,
                entidad,
                resultado.get("id"),
                resultado.get("mensaje", accion),
            )
            if clave:
                operaciones.registrar(
                    u["id"], clave, huella, json.dumps(resultado, ensure_ascii=True), ahora()
                )
            return resultado

    def consultar_operacion(self, token, clave):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            r = OperacionDAO(c).buscar(u["id"], clave)
            exigir(
                r is not None,
                "No hay una operación confirmada con esa clave para tu usuario.",
                "NO_EXISTE",
            )
            return {"fecha": r["fecha"], "resultado": json.loads(r["resultado"])}

    # ---------------------------- Administración
    def listar_usuarios(self, token):
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            return UsuarioDAO(c).listar()

    def guardar_usuario(
        self, token, nombre, login, rol, activo=True, password=None, uid=None
    ):
        nombre, login = v.texto(nombre, "Nombre"), v.login(login)
        exigir(rol in v.ROLES, "Rol inválido.")
        activo = v.booleano(activo)
        if password is not None:
            password = hash_clave(password)
        if uid is None:
            exigir(
                password is not None,
                "El nuevo usuario necesita una contraseña temporal.",
            )

        def accion(c, actor):
            usuarios = UsuarioDAO(c)
            if uid is None:
                ident = usuarios.crear(nombre, login, password, rol, activo, temporal=True)
            else:
                u = usuarios.obtener(uid)
                if actor["id"] == uid:
                    exigir(
                        rol == u["rol"] and activo,
                        "No puedes desactivarte ni cambiar tu propio rol.",
                    )
                    exigir(
                        password is None,
                        "Para tu contraseña usa Cambiar mi contraseña.",
                    )
                if rol != u["rol"] or not activo:
                    self._sin_pedidos_abiertos(c, uid)
                if (
                    u["activo"]
                    and u["rol"] == "ADMINISTRADOR"
                    and (not activo or rol != "ADMINISTRADOR")
                ):
                    exigir(usuarios.contar_administradores_activos() > 1, "Debe quedar un administrador activo.")
                usuarios.actualizar(uid, nombre, login, rol, activo)
                if password:
                    usuarios.cambiar_clave(uid, password, temporal=True)
                SesionDAO(c).revocar_usuario(uid)
                ident = uid
            return {
                "id": ident,
                "mensaje": "Usuario guardado. Si se asignó contraseña temporal, debe cambiarla al entrar.",
            }

        return self._ejecutar(
            token, "GUARDAR_USUARIO", "usuario", {}, accion, ("ADMINISTRADOR",)
        )

    def _sin_pedidos_abiertos(self, c, uid):
        exigir(
            not PedidoDAO(c).tiene_abiertos(uid),
            "El usuario tiene pedidos abiertos. Ciérralos o reasígnalos antes.",
            "CONFLICTO",
        )

    def desactivar_usuario(self, token, uid):
        def accion(c, actor):
            usuarios = UsuarioDAO(c)
            u = usuarios.obtener(uid)
            exigir(uid != actor["id"], "No puedes desactivarte.")
            self._sin_pedidos_abiertos(c, uid)
            if u["rol"] == "ADMINISTRADOR" and u["activo"]:
                exigir(usuarios.contar_administradores_activos() > 1, "Debe quedar un administrador activo.")
            usuarios.desactivar(uid)
            SesionDAO(c).revocar_usuario(uid)
            return {"id": uid, "mensaje": "Usuario desactivado; historial conservado."}

        return self._ejecutar(
            token, "DESACTIVAR_USUARIO", "usuario", {}, accion, ("ADMINISTRADOR",)
        )

    def categorias(self, token):
        with self.base.transaccion() as c:
            self._actor(c, token)
            return CategoriaDAO(c).listar()

    def guardar_categoria(self, token, nombre, cid=None):
        nombre = v.texto(nombre, "Categoría", 50)

        def accion(c, u):
            categorias = CategoriaDAO(c)
            if cid is None:
                ident = categorias.crear(nombre)
            else:
                categorias.obtener(cid)
                categorias.actualizar(cid, nombre)
                ident = cid
            return {"id": ident, "mensaje": "Categoría guardada."}

        return self._ejecutar(
            token, "GUARDAR_CATEGORIA", "categoria", {}, accion, ("ADMINISTRADOR",)
        )

    def eliminar_categoria(self, token, cid):
        def accion(c, u):
            categorias = CategoriaDAO(c)
            categorias.obtener(cid)
            exigir(
                not ProductoDAO(c).usa_categoria(cid),
                "La categoría tiene productos, incluso archivados. Reasígnalos antes.",
                "CONFLICTO",
            )
            exigir(
                not DetalleDAO(c).usa_categoria(cid),
                "La categoría forma parte de ventas históricas. Consérvala.",
                "CONFLICTO",
            )
            categorias.eliminar(cid)
            return {"id": cid, "mensaje": "Categoría vacía eliminada."}

        return self._ejecutar(
            token, "ELIMINAR_CATEGORIA", "categoria", {}, accion, ("ADMINISTRADOR",)
        )

    def productos(self, token, incluir_archivados=False):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            return ProductoDAO(c).listar(u["rol"] == "ADMINISTRADOR" and incluir_archivados)

    def guardar_producto(
        self,
        token,
        nombre,
        descripcion,
        precio,
        categoria_id,
        disponible=True,
        activo=True,
        pid=None,
    ):
        nombre = v.texto(nombre, "Producto")
        descripcion = v.texto(descripcion, "Descripción", 255, True)
        precio = v.centavos(precio)
        categoria_id = v.entero(categoria_id)
        disponible = v.booleano(disponible)
        activo = v.booleano(activo)

        def accion(c, u):
            CategoriaDAO(c).obtener(categoria_id)
            productos = ProductoDAO(c)
            params = (nombre, descripcion, precio, categoria_id, disponible, activo)
            if pid is None:
                ident = productos.crear(*params)
            else:
                productos.obtener(pid)
                productos.actualizar(pid, *params)
                ident = pid
            return {
                "id": ident,
                "mensaje": "Producto guardado. Los pedidos previos conservan su precio y nombre.",
            }

        return self._ejecutar(
            token, "GUARDAR_PRODUCTO", "producto", {}, accion, ("ADMINISTRADOR",)
        )

    def archivar_producto(self, token, pid):
        def accion(c, u):
            productos = ProductoDAO(c)
            productos.obtener(pid)
            productos.archivar(pid)
            return {
                "id": pid,
                "mensaje": "Producto archivado; detalles históricos conservados.",
            }

        return self._ejecutar(
            token, "ARCHIVAR_PRODUCTO", "producto", {}, accion, ("ADMINISTRADOR",)
        )

    def mesas(self, token, incluir_archivadas=False):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            return MesaDAO(c).listar(u["rol"] == "ADMINISTRADOR" and incluir_archivadas)

    def guardar_mesa(self, token, numero, capacidad=4, activa=True, mid=None):
        numero = v.entero(numero, "Número", 1, 9999)
        capacidad = v.entero(capacidad, "Capacidad", 1, 100)
        activa = v.booleano(activa)

        def accion(c, u):
            mesas = MesaDAO(c)
            if mid is None:
                ident = mesas.crear(numero, capacidad, activa)
            else:
                mesas.obtener(mid)
                exigir(
                    OcupacionDAO(c).buscar_por_mesa(mid) is None,
                    "No puedes modificar una mesa ocupada.",
                    "CONFLICTO",
                )
                mesas.actualizar(mid, numero, capacidad, activa)
                ident = mid
            return {"id": ident, "mensaje": "Mesa guardada."}

        return self._ejecutar(
            token, "GUARDAR_MESA", "mesa", {}, accion, ("ADMINISTRADOR",)
        )

    def archivar_mesa(self, token, mid):
        def accion(c, u):
            mesas = MesaDAO(c)
            mesas.obtener(mid)
            exigir(
                OcupacionDAO(c).buscar_por_mesa(mid) is None,
                "No puedes archivar una mesa ocupada.",
                "CONFLICTO",
            )
            mesas.archivar(mid)
            return {"id": mid, "mensaje": "Mesa archivada; historial conservado."}

        return self._ejecutar(
            token, "ARCHIVAR_MESA", "mesa", {}, accion, ("ADMINISTRADOR",)
        )

    # ---------------------------- Pedidos: Juan, mesero y supervisión del dueño
    def _pedido(self, c, u, pid, version=None, dao=None):
        p = (dao or PedidoDAO(c)).obtener(pid)
        exigir(
            u["rol"] != "MESERO" or p["responsable_id"] == u["id"],
            "El pedido pertenece a otra persona.",
            "PERMISO",
        )
        if version is not None:
            v.entero(version, "Versión")
            exigir(
                p["version"] == version,
                "El pedido cambió en otra sesión. Consúltalo otra vez.",
                "CONFLICTO",
            )
        return p

    def _resumen(self, c, pid):
        return dict(PedidoDAO(c).resumen(pid), total_centavos=DetalleDAO(c).total(pid))

    def _tocar(self, c, p):
        PedidoDAO(c).actualizar_version(p["id"], p["version"], ahora())

    def _historial(self, c, pid, estado, uid, motivo=""):
        HistorialDAO(c).registrar(pid, estado, uid, ahora(), motivo)

    def crear_pedido(self, token, tipo, mesa_id=None, responsable_id=None, clave=None):
        exigir(tipo in ("SALON", "LLEVAR"), "Tipo válido: SALON o LLEVAR.")
        exigir(
            (tipo == "SALON" and type(mesa_id) is int)
            or (tipo == "LLEVAR" and mesa_id is None),
            "Salón requiere mesa; para llevar no admite mesa.",
        )

        def accion(c, u):
            responsable = responsable_id if responsable_id is not None else u["id"]
            exigir(
                u["rol"] == "ADMINISTRADOR" or responsable == u["id"],
                "No puedes crear pedidos a nombre de otra persona.",
                "PERMISO",
            )
            usuario = UsuarioDAO(c).obtener(responsable)
            exigir(
                usuario["activo"] and usuario["rol"] in ("MESERO", "ADMINISTRADOR"),
                "Responsable no disponible.",
            )
            ocupacion = OcupacionDAO(c)
            if tipo == "SALON":
                m = MesaDAO(c).obtener(mesa_id)
                exigir(m["activa"], "Mesa fuera de servicio.", "CONFLICTO")
                exigir(
                    ocupacion.buscar_por_mesa(mesa_id) is None,
                    "Mesa ocupada. Selecciona otra o consulta su pedido.",
                    "CONFLICTO",
                )
            pid = PedidoDAO(c).crear(responsable, mesa_id, tipo, ahora())
            if mesa_id is not None:
                ocupacion.reservar(mesa_id, pid)
            self._historial(c, pid, "PENDIENTE", u["id"], "Creación del pedido.")
            return dict(
                self._resumen(c, pid),
                mensaje="Pedido creado en pendiente. Agrega productos antes de prepararlo.",
            )

        return self._ejecutar(
            token,
            "CREAR_PEDIDO",
            "pedido",
            {"tipo": tipo, "mesa": mesa_id, "responsable": responsable_id},
            accion,
            ("ADMINISTRADOR", "MESERO"),
            clave,
        )

    def listar_pedidos(self, token, estado=None, abiertos=False, pagina=1):
        v.entero(pagina, "Página", 1, 1000000)
        exigir(estado is None or estado in v.ESTADOS, "Estado inválido.")
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            return PedidoDAO(c).listar(
                pagina,
                responsable_id=u["id"] if u["rol"] == "MESERO" else None,
                estado=estado,
                abiertos=abiertos,
                ascendente=u["rol"] == "COCINA",
            )

    def cola_cocina(self, token, pagina=1):
        """Pedidos abiertos en orden de llegada, también para administración."""
        v.entero(pagina, "Página", 1, 1000000)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR", "COCINA"))
            return PedidoDAO(c).cola(pagina)

    def obtener_pedido(self, token, pid):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            p = self._pedido(c, u, pid)
            p["responsable"] = UsuarioDAO(c).obtener(p["responsable_id"])["nombre"]
            p["mesa"] = MesaDAO(c).obtener(p["mesa_id"])["numero"] if p["mesa_id"] else None
            p["detalles"] = DetalleDAO(c).listar(pid)
            p["total_centavos"] = sum(
                d["cantidad"] * d["precio_centavos"] for d in p["detalles"]
            )
            p["historial"] = HistorialDAO(c).listar_pedido(pid)
            return p

    def agregar_producto(
        self, token, pid, producto_id, cantidad, notas, version, clave=None
    ):
        v.entero(version, "Versión")
        v.entero(cantidad, "Cantidad", 1, 99)
        notas = v.texto(notas, "Notas", 255, True)

        def accion(c, u):
            # HU02: PedidoDAO valida el pedido, ProductoDAO carga precio y categoría,
            # y DetalleDAO guarda la línea; todos usan el mismo cursor transaccional.
            pedido_dao = PedidoDAO(c)
            producto_dao = ProductoDAO(c)
            detalle_dao = DetalleDAO(c)
            p = self._pedido(c, u, pid, version, dao=pedido_dao)
            exigir(
                p["estado"] == "PENDIENTE",
                "Solo puedes editar un pedido pendiente.",
                "ESTADO",
            )
            producto = producto_dao.obtener(producto_id)
            exigir(
                producto["activo"] and producto["disponible"],
                "Producto no disponible.",
                "CONFLICTO",
            )
            exigir(
                detalle_dao.contar(pid) < 100, "Máximo 100 líneas por pedido."
            )
            detalle_dao.crear(pid, producto, cantidad, notas)
            self._tocar(c, p)
            return dict(
                self._resumen(c, pid),
                mensaje="Producto agregado; precio histórico registrado.",
            )

        return self._ejecutar(
            token,
            "AGREGAR_PRODUCTO",
            "pedido",
            {
                "pedido": pid,
                "producto": producto_id,
                "cantidad": cantidad,
                "notas": notas,
                "version": version,
            },
            accion,
            ("ADMINISTRADOR", "MESERO"),
            clave,
        )

    def editar_detalle(self, token, pid, did, cantidad, notas, version, clave=None):
        v.entero(version, "Versión")
        v.entero(cantidad, "Cantidad", 1, 99)
        notas = v.texto(notas, "Notas", 255, True)

        def accion(c, u):
            p = self._pedido(c, u, pid, version)
            exigir(
                p["estado"] == "PENDIENTE",
                "Solo puedes editar un pedido pendiente.",
                "ESTADO",
            )
            detalles = DetalleDAO(c)
            d = detalles.obtener(did)
            exigir(
                d["pedido_id"] == pid, "La línea no pertenece al pedido.", "NO_EXISTE"
            )
            detalles.actualizar(did, cantidad, notas)
            self._tocar(c, p)
            return dict(self._resumen(c, pid), mensaje="Cantidad y notas actualizadas.")

        return self._ejecutar(
            token,
            "EDITAR_DETALLE",
            "pedido",
            {
                "pedido": pid,
                "linea": did,
                "cantidad": cantidad,
                "notas": notas,
                "version": version,
            },
            accion,
            ("ADMINISTRADOR", "MESERO"),
            clave,
        )

    def quitar_detalle(self, token, pid, did, version, clave=None):
        v.entero(version, "Versión")

        def accion(c, u):
            p = self._pedido(c, u, pid, version)
            exigir(
                p["estado"] == "PENDIENTE",
                "Solo puedes quitar productos de un pedido pendiente.",
                "ESTADO",
            )
            detalles = DetalleDAO(c)
            d = detalles.obtener(did)
            exigir(
                d["pedido_id"] == pid, "La línea no pertenece al pedido.", "NO_EXISTE"
            )
            detalles.eliminar(did)
            self._tocar(c, p)
            return dict(self._resumen(c, pid), mensaje="Línea retirada del pedido.")

        return self._ejecutar(
            token,
            "QUITAR_DETALLE",
            "pedido",
            {"pedido": pid, "linea": did, "version": version},
            accion,
            ("ADMINISTRADOR", "MESERO"),
            clave,
        )

    def cambiar_estado(self, token, pid, nuevo, version, motivo="", clave=None):
        v.entero(version, "Versión")
        exigir(nuevo in v.ESTADOS, "Estado inválido.")
        motivo = v.texto(motivo, "Motivo", 255, True)

        def accion(c, u):
            p = self._pedido(c, u, pid, version)
            if nuevo in ("EN_PREPARACION", "LISTO"):
                exigir(
                    u["rol"] in ("COCINA", "ADMINISTRADOR"),
                    "Solo cocina o administración prepara pedidos.",
                    "PERMISO",
                )
                exigir(
                    (p["estado"], nuevo)
                    in (("PENDIENTE", "EN_PREPARACION"), ("EN_PREPARACION", "LISTO")),
                    "No puedes saltar ni repetir estados.",
                    "ESTADO",
                )
                exigir(
                    DetalleDAO(c).tiene_lineas(pid),
                    "No puedes preparar un pedido vacío.",
                    "ESTADO",
                )
                if nuevo == "EN_PREPARACION":
                    PedidoDAO(c).asignar_cocinero(pid, u["id"])
                elif u["rol"] == "COCINA":
                    exigir(
                        p["cocinero_id"] == u["id"],
                        "Otro cocinero tomó este pedido. Solicita reasignación al administrador.",
                        "PERMISO",
                    )
            elif nuevo == "ENTREGADO":
                exigir(
                    u["rol"] in ("MESERO", "ADMINISTRADOR"),
                    "Solo mesero o administración entrega pedidos.",
                    "PERMISO",
                )
                exigir(
                    p["estado"] == "LISTO",
                    "Solo puedes entregar un pedido listo.",
                    "ESTADO",
                )
            elif nuevo == "CANCELADO":
                exigir(
                    u["rol"] in ("MESERO", "ADMINISTRADOR"),
                    "Solo mesero o administración cancela pedidos.",
                    "PERMISO",
                )
                permitidos = (
                    ("PENDIENTE", "EN_PREPARACION", "LISTO")
                    if u["rol"] == "ADMINISTRADOR"
                    else ("PENDIENTE", "EN_PREPARACION")
                )
                exigir(
                    p["estado"] in permitidos,
                    "No puedes cancelar este pedido en su estado actual.",
                    "ESTADO",
                )
                exigir(bool(motivo), "La cancelación necesita motivo.")
            else:
                exigir(False, "No existe transición de regreso a pendiente.", "ESTADO")
            self._tocar(c, p)
            PedidoDAO(c).cambiar_estado(pid, nuevo, motivo if nuevo == "CANCELADO" else None)
            self._historial(c, pid, nuevo, u["id"], motivo)
            if nuevo in ("ENTREGADO", "CANCELADO") and p["mesa_id"] is not None:
                exigir(
                    OcupacionDAO(c).liberar(p["mesa_id"], pid) == 1,
                    "Reserva de mesa inconsistente. No se confirmó el cierre.",
                    "INTEGRIDAD",
                )
            return dict(
                self._resumen(c, pid), mensaje="Estado actualizado a " + nuevo + "."
            )

        return self._ejecutar(
            token,
            "CAMBIAR_ESTADO",
            "pedido",
            {"pedido": pid, "nuevo": nuevo, "version": version, "motivo": motivo},
            accion,
            TODOS,
            clave,
        )

    def reasignar_pedido(
        self, token, pid, responsable_id, cocinero_id, version, motivo, clave=None
    ):
        v.entero(version, "Versión")
        motivo = v.texto(motivo, "Motivo", 255)
        exigir(
            responsable_id is not None or cocinero_id is not None,
            "Selecciona al menos una reasignación.",
        )

        def accion(c, u):
            p = self._pedido(c, u, pid, version)
            exigir(
                p["estado"] in v.ABIERTOS,
                "No puedes reasignar un pedido cerrado.",
                "ESTADO",
            )
            if responsable_id is not None:
                r = UsuarioDAO(c).obtener(responsable_id)
                exigir(
                    r["activo"] and r["rol"] in ("MESERO", "ADMINISTRADOR"),
                    "Responsable no habilitado.",
                )
                PedidoDAO(c).asignar_responsable(pid, responsable_id)
            if cocinero_id is not None:
                exigir(
                    p["estado"] == "EN_PREPARACION",
                    "Solo se reasigna cocina mientras está en preparación.",
                    "ESTADO",
                )
                k = UsuarioDAO(c).obtener(cocinero_id)
                exigir(
                    k["activo"] and k["rol"] in ("COCINA", "ADMINISTRADOR"),
                    "Cocinero no habilitado.",
                )
                PedidoDAO(c).asignar_cocinero(pid, cocinero_id)
            self._tocar(c, p)
            return dict(
                self._resumen(c, pid),
                mensaje=f"Reasignación: responsable={responsable_id}, cocina={cocinero_id}. Motivo: {motivo}",
            )

        return self._ejecutar(
            token,
            "REASIGNAR_PEDIDO",
            "pedido",
            {
                "pedido": pid,
                "responsable": responsable_id,
                "cocinero": cocinero_id,
                "version": version,
                "motivo": motivo,
            },
            accion,
            ("ADMINISTRADOR",),
            clave,
        )

    # ---------------------------- Consultas, reportes y auditoría
    def auditoria(self, token, pagina=1):
        v.entero(pagina, "Página", 1, 1000000)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            return AuditoriaDAO(c).listar(pagina)

    def ventas(self, token, desde, hasta, categoria_id=None, producto_id=None):
        inicio, fin = rango_utc_colombia(desde, hasta)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            filas = ReporteDAO(c).ventas_entregadas(
                inicio, fin,
                v.entero(categoria_id) if categoria_id is not None else None,
                v.entero(producto_id) if producto_id is not None else None,
            )
            grupos = {}
            pedidos = set()
            total = unidades = 0
            for d in filas:
                llave = (d["producto_id"], d["producto_nombre"], d["categoria_nombre"])
                g = grupos.setdefault(
                    llave,
                    {
                        "producto_id": d["producto_id"],
                        "producto": d["producto_nombre"],
                        "categoria": d["categoria_nombre"],
                        "unidades": 0,
                        "total_centavos": 0,
                    },
                )
                subtotal = d["cantidad"] * d["precio_centavos"]
                g["unidades"] += d["cantidad"]
                g["total_centavos"] += subtotal
                total += subtotal
                unidades += d["cantidad"]
                pedidos.add(d["pedido_id"])
            return {
                "total_centavos": total,
                "unidades": unidades,
                "pedidos": len(pedidos),
                "items": list(grupos.values()),
                "zona": ZONA_COLOMBIA,
            }

    def tiempos(self, token, desde, hasta):
        inicio, fin = rango_utc_colombia(desde, hasta)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            filas = ReporteDAO(c).preparaciones(inicio, fin)
            for r in filas:
                comienzo = leer_instante_utc(r["inicio"])
                listo = leer_instante_utc(r["listo"])
                r["segundos"] = round((listo - comienzo).total_seconds(), 3)
                r["inicio"] = comienzo.astimezone(BOGOTA).isoformat(timespec="microseconds")
                r["listo"] = listo.astimezone(BOGOTA).isoformat(timespec="microseconds")
            return {
                "items": filas,
                "promedio_segundos": (
                    round(sum(r["segundos"] for r in filas) / len(filas), 3)
                    if filas
                    else None
                ),
                "zona": ZONA_COLOMBIA,
            }

    def inspeccionar(self, token, tabla, pagina=1):
        exigir(
            tabla in TABLAS,
            "Tabla no disponible. Sesiones y credenciales no se muestran.",
        )
        v.entero(pagina, "Página", 1, 1000000)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            return inspeccionar_tabla(c, tabla, pagina)

    def respaldar(self, token, destino):
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
        ruta = self.base.respaldo_sqlite(destino)
        return {
            "ruta": ruta,
            "mensaje": "Respaldo completo guardado. Contiene datos y hashes: consérvalo en privado.",
        }
