"""Reglas del restaurante sobre SQL parametrizado: INSERT, SELECT, UPDATE y DELETE.
Todos los permisos se verifican aquí. La API no acepta una identidad sin autenticar.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
import secrets
from uuid import UUID
from .errores import exigir, ErrorNegocio
from .seguridad import hash_clave, verificar_clave, huella_token
from . import validaciones as v

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
            c.execute("SELECT COUNT(*) AS n FROM usuario")
            return c.one()["n"] == 0

    def crear_primer_admin(self, nombre, login, password):
        nombre, login, password = (
            v.texto(nombre, "Nombre"),
            v.login(login),
            v.clave(password),
        )
        h = hash_clave(password)
        with self.base.transaccion(True) as c:
            c.execute("SELECT COUNT(*) AS n FROM usuario")
            exigir(
                c.one()["n"] == 0,
                "Ya hay usuarios. El primer administrador ya fue configurado.",
                "YA_CONFIGURADO",
            )
            c.execute(
                "INSERT INTO usuario(nombre,login,password_hash,rol,activo,debe_cambiar) VALUES(?,?,?,?,1,0)",
                (nombre, login, h, "ADMINISTRADOR"),
            )
            uid = c.lastrowid
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
            c.execute("SELECT * FROM usuario WHERE login=?", (login,))
            u = c.one()
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
                c.execute(
                    "UPDATE usuario SET fallos=?,bloqueado_hasta=? WHERE id=?",
                    (fallos, bloqueo, u["id"]),
                )
                error = ErrorNegocio(
                    "CREDENCIALES", "Usuario o contraseña incorrectos."
                )
            else:
                token = secrets.token_urlsafe(32)
                c.execute(
                    "UPDATE usuario SET fallos=0,bloqueado_hasta=NULL WHERE id=?",
                    (u["id"],),
                )
                c.execute("DELETE FROM sesion WHERE expira<=?", (ahora(),))
                c.execute(
                    "INSERT INTO sesion(token_hash,usuario_id,creado,expira) VALUES(?,?,?,?)",
                    (huella_token(token), u["id"], ahora(), despues(horas=8)),
                )
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
        c.execute(
            "SELECT u.id,u.nombre,u.login,u.rol,u.activo,u.debe_cambiar,s.expira "
            "FROM sesion s JOIN usuario u ON u.id=s.usuario_id WHERE s.token_hash=?",
            (huella_token(token),),
        )
        u = c.one()
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
            c.execute("DELETE FROM sesion WHERE token_hash=?", (huella_token(token),))

    def cambiar_clave(self, token, actual, nueva):
        nueva = v.clave(nueva)
        with self.base.transaccion(True) as c:
            u = self._actor(c, token, permite_cambio=True)
            c.execute("SELECT password_hash FROM usuario WHERE id=?", (u["id"],))
            exigir(
                verificar_clave(actual, c.one()["password_hash"]),
                "La contraseña actual no coincide.",
            )
            exigir(actual != nueva, "La contraseña nueva debe ser diferente.")
            c.execute(
                "UPDATE usuario SET password_hash=?,debe_cambiar=0,fallos=0,bloqueado_hasta=NULL WHERE id=?",
                (hash_clave(nueva), u["id"]),
            )
            c.execute("DELETE FROM sesion WHERE usuario_id=?", (u["id"],))
            self._auditar(
                c,
                u["id"],
                "CAMBIAR_CLAVE",
                "usuario",
                u["id"],
                "Contraseña propia actualizada; sesiones revocadas.",
            )

    def _auditar(self, c, uid, accion, entidad, eid, descripcion):
        c.execute(
            "INSERT INTO auditoria(usuario_id,accion,entidad,entidad_id,fecha,descripcion) VALUES(?,?,?,?,?,?)",
            (uid, accion, entidad, eid, ahora(), descripcion),
        )

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
            if clave:
                c.execute(
                    "SELECT huella,resultado FROM operacion WHERE usuario_id=? AND clave=?",
                    (u["id"], clave),
                )
                anterior = c.one()
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
                c.execute(
                    "INSERT INTO operacion(usuario_id,clave,huella,resultado,fecha) VALUES(?,?,?,?,?)",
                    (
                        u["id"],
                        clave,
                        huella,
                        json.dumps(resultado, ensure_ascii=True),
                        ahora(),
                    ),
                )
            return resultado

    def consultar_operacion(self, token, clave):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            c.execute(
                "SELECT resultado,fecha FROM operacion WHERE usuario_id=? AND clave=?",
                (u["id"], clave),
            )
            r = c.one()
            exigir(
                r is not None,
                "No hay una operación confirmada con esa clave para tu usuario.",
                "NO_EXISTE",
            )
            return {"fecha": r["fecha"], "resultado": json.loads(r["resultado"])}

    def _fila(self, c, tabla, identificador):
        exigir(
            tabla in {"usuario", "categoria", "producto", "mesa", "pedido", "detalle"},
            "Entidad no válida.",
        )
        identificador = v.entero(identificador)
        c.execute(f"SELECT * FROM {tabla} WHERE id=?", (identificador,))
        fila = c.one()
        exigir(
            fila is not None, f"No existe {tabla} con ID {identificador}.", "NO_EXISTE"
        )
        return fila

    # ---------------------------- Administración
    def listar_usuarios(self, token):
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            c.execute(
                "SELECT id,nombre,login,rol,activo,debe_cambiar,bloqueado_hasta FROM usuario ORDER BY id"
            )
            return c.all()

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
            if uid is None:
                c.execute(
                    "INSERT INTO usuario(nombre,login,password_hash,rol,activo,debe_cambiar) VALUES(?,?,?,?,?,1)",
                    (nombre, login, password, rol, activo),
                )
                ident = c.lastrowid
            else:
                u = self._fila(c, "usuario", uid)
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
                    c.execute(
                        "SELECT COUNT(*) AS n FROM usuario WHERE activo=1 AND rol='ADMINISTRADOR'"
                    )
                    exigir(c.one()["n"] > 1, "Debe quedar un administrador activo.")
                c.execute(
                    "UPDATE usuario SET nombre=?,login=?,rol=?,activo=? WHERE id=?",
                    (nombre, login, rol, activo, uid),
                )
                if password:
                    c.execute(
                        "UPDATE usuario SET password_hash=?,debe_cambiar=1,fallos=0,bloqueado_hasta=NULL WHERE id=?",
                        (password, uid),
                    )
                c.execute("DELETE FROM sesion WHERE usuario_id=?", (uid,))
                ident = uid
            return {
                "id": ident,
                "mensaje": "Usuario guardado. Si se asignó contraseña temporal, debe cambiarla al entrar.",
            }

        return self._ejecutar(
            token, "GUARDAR_USUARIO", "usuario", {}, accion, ("ADMINISTRADOR",)
        )

    def _sin_pedidos_abiertos(self, c, uid):
        c.execute(
            "SELECT id FROM pedido WHERE (responsable_id=? OR cocinero_id=?) AND estado IN ('PENDIENTE','EN_PREPARACION','LISTO') LIMIT 1",
            (uid, uid),
        )
        exigir(
            c.one() is None,
            "El usuario tiene pedidos abiertos. Ciérralos o reasígnalos antes.",
            "CONFLICTO",
        )

    def desactivar_usuario(self, token, uid):
        def accion(c, actor):
            u = self._fila(c, "usuario", uid)
            exigir(uid != actor["id"], "No puedes desactivarte.")
            self._sin_pedidos_abiertos(c, uid)
            if u["rol"] == "ADMINISTRADOR" and u["activo"]:
                c.execute(
                    "SELECT COUNT(*) AS n FROM usuario WHERE rol='ADMINISTRADOR' AND activo=1"
                )
                exigir(c.one()["n"] > 1, "Debe quedar un administrador activo.")
            c.execute("UPDATE usuario SET activo=0 WHERE id=?", (uid,))
            c.execute("DELETE FROM sesion WHERE usuario_id=?", (uid,))
            return {"id": uid, "mensaje": "Usuario desactivado; historial conservado."}

        return self._ejecutar(
            token, "DESACTIVAR_USUARIO", "usuario", {}, accion, ("ADMINISTRADOR",)
        )

    def categorias(self, token):
        with self.base.transaccion() as c:
            self._actor(c, token)
            c.execute("SELECT id,nombre FROM categoria ORDER BY nombre")
            return c.all()

    def guardar_categoria(self, token, nombre, cid=None):
        nombre = v.texto(nombre, "Categoría", 50)

        def accion(c, u):
            if cid is None:
                c.execute("INSERT INTO categoria(nombre) VALUES(?)", (nombre,))
                ident = c.lastrowid
            else:
                self._fila(c, "categoria", cid)
                c.execute("UPDATE categoria SET nombre=? WHERE id=?", (nombre, cid))
                ident = cid
            return {"id": ident, "mensaje": "Categoría guardada."}

        return self._ejecutar(
            token, "GUARDAR_CATEGORIA", "categoria", {}, accion, ("ADMINISTRADOR",)
        )

    def eliminar_categoria(self, token, cid):
        def accion(c, u):
            self._fila(c, "categoria", cid)
            c.execute("SELECT id FROM producto WHERE categoria_id=? LIMIT 1", (cid,))
            exigir(
                c.one() is None,
                "La categoría tiene productos, incluso archivados. Reasígnalos antes.",
                "CONFLICTO",
            )
            c.execute("SELECT id FROM detalle WHERE categoria_id=? LIMIT 1", (cid,))
            exigir(
                c.one() is None,
                "La categoría forma parte de ventas históricas. Consérvala.",
                "CONFLICTO",
            )
            c.execute("DELETE FROM categoria WHERE id=?", (cid,))
            return {"id": cid, "mensaje": "Categoría vacía eliminada."}

        return self._ejecutar(
            token, "ELIMINAR_CATEGORIA", "categoria", {}, accion, ("ADMINISTRADOR",)
        )

    def productos(self, token, incluir_archivados=False):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            q = "SELECT p.*,ca.nombre AS categoria FROM producto p JOIN categoria ca ON ca.id=p.categoria_id"
            if u["rol"] != "ADMINISTRADOR" or not incluir_archivados:
                q += " WHERE p.activo=1 AND p.disponible=1"
            c.execute(q + " ORDER BY ca.nombre,p.nombre,p.id")
            return c.all()

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
            self._fila(c, "categoria", categoria_id)
            params = (nombre, descripcion, precio, categoria_id, disponible, activo)
            if pid is None:
                c.execute(
                    "INSERT INTO producto(nombre,descripcion,precio_centavos,categoria_id,disponible,activo) VALUES(?,?,?,?,?,?)",
                    params,
                )
                ident = c.lastrowid
            else:
                self._fila(c, "producto", pid)
                c.execute(
                    "UPDATE producto SET nombre=?,descripcion=?,precio_centavos=?,categoria_id=?,disponible=?,activo=? WHERE id=?",
                    params + (pid,),
                )
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
            self._fila(c, "producto", pid)
            c.execute("UPDATE producto SET activo=0,disponible=0 WHERE id=?", (pid,))
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
            q = "SELECT m.*,CASE WHEN o.pedido_id IS NULL THEN 'LIBRE' ELSE 'OCUPADA' END AS estado,o.pedido_id FROM mesa m LEFT JOIN ocupacion o ON o.mesa_id=m.id"
            if u["rol"] != "ADMINISTRADOR" or not incluir_archivadas:
                q += " WHERE m.activa=1"
            c.execute(q + " ORDER BY m.numero")
            return c.all()

    def guardar_mesa(self, token, numero, capacidad=4, activa=True, mid=None):
        numero = v.entero(numero, "Número", 1, 9999)
        capacidad = v.entero(capacidad, "Capacidad", 1, 100)
        activa = v.booleano(activa)

        def accion(c, u):
            if mid is None:
                c.execute(
                    "INSERT INTO mesa(numero,capacidad,activa) VALUES(?,?,?)",
                    (numero, capacidad, activa),
                )
                ident = c.lastrowid
            else:
                self._fila(c, "mesa", mid)
                c.execute("SELECT pedido_id FROM ocupacion WHERE mesa_id=?", (mid,))
                exigir(
                    c.one() is None,
                    "No puedes modificar una mesa ocupada.",
                    "CONFLICTO",
                )
                c.execute(
                    "UPDATE mesa SET numero=?,capacidad=?,activa=? WHERE id=?",
                    (numero, capacidad, activa, mid),
                )
                ident = mid
            return {"id": ident, "mensaje": "Mesa guardada."}

        return self._ejecutar(
            token, "GUARDAR_MESA", "mesa", {}, accion, ("ADMINISTRADOR",)
        )

    def archivar_mesa(self, token, mid):
        def accion(c, u):
            self._fila(c, "mesa", mid)
            c.execute("SELECT pedido_id FROM ocupacion WHERE mesa_id=?", (mid,))
            exigir(c.one() is None, "No puedes archivar una mesa ocupada.", "CONFLICTO")
            c.execute("UPDATE mesa SET activa=0 WHERE id=?", (mid,))
            return {"id": mid, "mensaje": "Mesa archivada; historial conservado."}

        return self._ejecutar(
            token, "ARCHIVAR_MESA", "mesa", {}, accion, ("ADMINISTRADOR",)
        )

    # ---------------------------- Pedidos: Juan, mesero y supervisión del dueño
    def _pedido(self, c, u, pid, version=None):
        p = self._fila(c, "pedido", pid)
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
        c.execute("SELECT id,estado,version FROM pedido WHERE id=?", (pid,))
        p = c.one()
        c.execute(
            "SELECT COALESCE(SUM(precio_centavos*cantidad),0) AS total FROM detalle WHERE pedido_id=?",
            (pid,),
        )
        return {
            "id": pid,
            "estado": p["estado"],
            "version": p["version"],
            "total_centavos": int(c.one()["total"]),
        }

    def _tocar(self, c, p):
        c.execute(
            "UPDATE pedido SET actualizado=?,version=version+1 WHERE id=? AND version=?",
            (ahora(), p["id"], p["version"]),
        )
        exigir(c.rowcount == 1, "El pedido cambió; vuelve a consultarlo.", "CONFLICTO")

    def _historial(self, c, pid, estado, uid, motivo=""):
        c.execute(
            "INSERT INTO historial(pedido_id,estado,usuario_id,fecha,motivo) VALUES(?,?,?,?,?)",
            (pid, estado, uid, ahora(), motivo),
        )

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
            usuario = self._fila(c, "usuario", responsable)
            exigir(
                usuario["activo"] and usuario["rol"] in ("MESERO", "ADMINISTRADOR"),
                "Responsable no disponible.",
            )
            if tipo == "SALON":
                m = self._fila(c, "mesa", mesa_id)
                exigir(m["activa"], "Mesa fuera de servicio.", "CONFLICTO")
                c.execute("SELECT pedido_id FROM ocupacion WHERE mesa_id=?", (mesa_id,))
                exigir(
                    c.one() is None,
                    "Mesa ocupada. Selecciona otra o consulta su pedido.",
                    "CONFLICTO",
                )
            fecha = ahora()
            c.execute(
                "INSERT INTO pedido(responsable_id,mesa_id,tipo,estado,creado,actualizado,version) VALUES(?,?,?,'PENDIENTE',?,?,1)",
                (responsable, mesa_id, tipo, fecha, fecha),
            )
            pid = c.lastrowid
            if mesa_id is not None:
                c.execute(
                    "INSERT INTO ocupacion(mesa_id,pedido_id) VALUES(?,?)",
                    (mesa_id, pid),
                )
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
            q = "SELECT p.*,r.nombre AS responsable,co.nombre AS cocinero,m.numero AS mesa,COALESCE((SELECT SUM(d.precio_centavos*d.cantidad) FROM detalle d WHERE d.pedido_id=p.id),0) AS total_centavos FROM pedido p JOIN usuario r ON r.id=p.responsable_id LEFT JOIN usuario co ON co.id=p.cocinero_id LEFT JOIN mesa m ON m.id=p.mesa_id WHERE 1=1"
            params = []
            if u["rol"] == "MESERO":
                q += " AND p.responsable_id=?"
                params.append(u["id"])
            if abiertos:
                q += " AND p.estado IN ('PENDIENTE','EN_PREPARACION','LISTO')"
            if estado:
                q += " AND p.estado=?"
                params.append(estado)
            q += (
                " ORDER BY p.creado "
                + ("ASC" if u["rol"] == "COCINA" else "DESC")
                + ",p.id "
                + ("ASC" if u["rol"] == "COCINA" else "DESC")
                + " LIMIT 51 OFFSET ?"
            )
            c.execute(q, tuple(params) + ((pagina - 1) * 50,))
            filas = c.all()
            for f in filas:
                f["total_centavos"] = int(f["total_centavos"])
            return {"items": filas[:50], "hay_mas": len(filas) > 50, "pagina": pagina}

    def cola_cocina(self, token, pagina=1):
        """Pedidos abiertos en orden de llegada, también para administración."""
        v.entero(pagina, "Página", 1, 1000000)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR", "COCINA"))
            c.execute(
                "SELECT p.*,r.nombre AS responsable,m.numero AS mesa FROM pedido p "
                "JOIN usuario r ON r.id=p.responsable_id LEFT JOIN mesa m ON m.id=p.mesa_id "
                "WHERE p.estado IN ('PENDIENTE','EN_PREPARACION','LISTO') "
                "ORDER BY p.creado,p.id LIMIT 51 OFFSET ?",
                ((pagina - 1) * 50,),
            )
            filas = c.all()
            return {"items": filas[:50], "hay_mas": len(filas) > 50, "pagina": pagina}

    def obtener_pedido(self, token, pid):
        with self.base.transaccion() as c:
            u = self._actor(c, token)
            p = self._pedido(c, u, pid)
            c.execute("SELECT nombre FROM usuario WHERE id=?", (p["responsable_id"],))
            p["responsable"] = c.one()["nombre"]
            p["mesa"] = None
            if p["mesa_id"]:
                c.execute("SELECT numero FROM mesa WHERE id=?", (p["mesa_id"],))
                p["mesa"] = c.one()["numero"]
            c.execute("SELECT * FROM detalle WHERE pedido_id=? ORDER BY id", (pid,))
            p["detalles"] = c.all()
            p["total_centavos"] = sum(
                d["cantidad"] * d["precio_centavos"] for d in p["detalles"]
            )
            c.execute(
                "SELECT h.*,u.nombre AS usuario FROM historial h JOIN usuario u ON u.id=h.usuario_id WHERE pedido_id=? ORDER BY h.id",
                (pid,),
            )
            p["historial"] = c.all()
            return p

    def agregar_producto(
        self, token, pid, producto_id, cantidad, notas, version, clave=None
    ):
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
            producto = self._fila(c, "producto", producto_id)
            exigir(
                producto["activo"] and producto["disponible"],
                "Producto no disponible.",
                "CONFLICTO",
            )
            c.execute("SELECT COUNT(*) AS n FROM detalle WHERE pedido_id=?", (pid,))
            exigir(c.one()["n"] < 100, "Máximo 100 líneas por pedido.")
            ca = self._fila(c, "categoria", producto["categoria_id"])
            c.execute(
                "INSERT INTO detalle(pedido_id,producto_id,categoria_id,producto_nombre,categoria_nombre,precio_centavos,cantidad,notas) VALUES(?,?,?,?,?,?,?,?)",
                (
                    pid,
                    producto_id,
                    ca["id"],
                    producto["nombre"],
                    ca["nombre"],
                    producto["precio_centavos"],
                    cantidad,
                    notas,
                ),
            )
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
            d = self._fila(c, "detalle", did)
            exigir(
                d["pedido_id"] == pid, "La línea no pertenece al pedido.", "NO_EXISTE"
            )
            c.execute(
                "UPDATE detalle SET cantidad=?,notas=? WHERE id=?",
                (cantidad, notas, did),
            )
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
            d = self._fila(c, "detalle", did)
            exigir(
                d["pedido_id"] == pid, "La línea no pertenece al pedido.", "NO_EXISTE"
            )
            c.execute("DELETE FROM detalle WHERE id=?", (did,))
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
                c.execute("SELECT id FROM detalle WHERE pedido_id=? LIMIT 1", (pid,))
                exigir(
                    c.one() is not None, "No puedes preparar un pedido vacío.", "ESTADO"
                )
                if nuevo == "EN_PREPARACION":
                    c.execute(
                        "UPDATE pedido SET cocinero_id=? WHERE id=?", (u["id"], pid)
                    )
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
                c.execute(
                    "UPDATE pedido SET motivo_cancelacion=? WHERE id=?", (motivo, pid)
                )
            else:
                exigir(False, "No existe transición de regreso a pendiente.", "ESTADO")
            self._tocar(c, p)
            c.execute("UPDATE pedido SET estado=? WHERE id=?", (nuevo, pid))
            self._historial(c, pid, nuevo, u["id"], motivo)
            if nuevo in ("ENTREGADO", "CANCELADO") and p["mesa_id"] is not None:
                c.execute(
                    "DELETE FROM ocupacion WHERE mesa_id=? AND pedido_id=?",
                    (p["mesa_id"], pid),
                )
                exigir(
                    c.rowcount == 1,
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
                r = self._fila(c, "usuario", responsable_id)
                exigir(
                    r["activo"] and r["rol"] in ("MESERO", "ADMINISTRADOR"),
                    "Responsable no habilitado.",
                )
                c.execute(
                    "UPDATE pedido SET responsable_id=? WHERE id=?",
                    (responsable_id, pid),
                )
            if cocinero_id is not None:
                exigir(
                    p["estado"] == "EN_PREPARACION",
                    "Solo se reasigna cocina mientras está en preparación.",
                    "ESTADO",
                )
                k = self._fila(c, "usuario", cocinero_id)
                exigir(
                    k["activo"] and k["rol"] in ("COCINA", "ADMINISTRADOR"),
                    "Cocinero no habilitado.",
                )
                c.execute(
                    "UPDATE pedido SET cocinero_id=? WHERE id=?", (cocinero_id, pid)
                )
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
            c.execute(
                "SELECT a.*,u.login AS usuario FROM auditoria a JOIN usuario u ON u.id=a.usuario_id ORDER BY a.id DESC LIMIT 51 OFFSET ?",
                ((pagina - 1) * 50,),
            )
            filas = c.all()
            return {"items": filas[:50], "hay_mas": len(filas) > 50, "pagina": pagina}

    def _rango(self, desde, hasta):
        try:
            inicio = datetime.strptime(desde, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            fin = datetime.strptime(hasta, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)
            exigir(
                0 < (fin - inicio).days <= 366,
                "Periodo inválido: máximo 366 días e inicio anterior o igual al final.",
            )
            return inicio.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), fin.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        except (ValueError, TypeError, OverflowError):
            raise ErrorNegocio(
                "DATO_INVALIDO", "Fechas válidas con formato AAAA-MM-DD."
            ) from None

    def ventas(self, token, desde, hasta, categoria_id=None, producto_id=None):
        inicio, fin = self._rango(desde, hasta)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            q = "SELECT p.id AS pedido_id,d.producto_id,d.producto_nombre,d.categoria_nombre,d.cantidad,d.precio_centavos FROM detalle d JOIN pedido p ON p.id=d.pedido_id JOIN historial h ON h.pedido_id=p.id AND h.estado='ENTREGADO' WHERE p.estado='ENTREGADO' AND h.fecha>=? AND h.fecha<?"
            params = [inicio, fin]
            if categoria_id is not None:
                q += " AND d.categoria_id=?"
                params.append(v.entero(categoria_id))
            if producto_id is not None:
                q += " AND d.producto_id=?"
                params.append(v.entero(producto_id))
            c.execute(q, tuple(params))
            filas = c.all()
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
                "zona": "UTC",
            }

    def tiempos(self, token, desde, hasta):
        inicio, fin = self._rango(desde, hasta)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            c.execute(
                "SELECT p.id,h1.fecha AS inicio,h2.fecha AS listo FROM pedido p JOIN historial h1 ON h1.pedido_id=p.id AND h1.estado='EN_PREPARACION' JOIN historial h2 ON h2.pedido_id=p.id AND h2.estado='LISTO' WHERE p.estado<>'CANCELADO' AND h2.fecha>=? AND h2.fecha<? ORDER BY p.id",
                (inicio, fin),
            )
            filas = c.all()
            for r in filas:
                r["segundos"] = round(
                    (
                        datetime.fromisoformat(r["listo"].replace("Z", "+00:00"))
                        - datetime.fromisoformat(r["inicio"].replace("Z", "+00:00"))
                    ).total_seconds(),
                    3,
                )
            return {
                "items": filas,
                "promedio_segundos": (
                    round(sum(r["segundos"] for r in filas) / len(filas), 3)
                    if filas
                    else None
                ),
                "zona": "UTC",
            }

    def inspeccionar(self, token, tabla, pagina=1):
        permitidas = {
            "usuario": "id,nombre,login,rol,activo,debe_cambiar",
            "categoria": "*",
            "producto": "*",
            "mesa": "*",
            "pedido": "*",
            "ocupacion": "*",
            "detalle": "*",
            "historial": "*",
            "auditoria": "*",
            "sistema": "*",
        }
        exigir(
            tabla in permitidas,
            "Tabla no disponible. Sesiones y credenciales no se muestran.",
        )
        v.entero(pagina, "Página", 1, 1000000)
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
            orden = "mesa_id" if tabla == "ocupacion" else "id"
            c.execute(
                f"SELECT {permitidas[tabla]} FROM {tabla} ORDER BY {orden} LIMIT 51 OFFSET ?",
                ((pagina - 1) * 50,),
            )
            filas = c.all()
            return {"items": filas[:50], "hay_mas": len(filas) > 50, "pagina": pagina}

    def respaldar(self, token, destino):
        with self.base.transaccion() as c:
            self._actor(c, token, ("ADMINISTRADOR",))
        ruta = self.base.respaldo_sqlite(destino)
        return {
            "ruta": ruta,
            "mensaje": "Respaldo completo guardado. Contiene datos y hashes: consérvalo en privado.",
        }
