"""Adaptador HTTP: JSON y códigos HTTP; las reglas y SQL viven en servicio.py."""

from functools import wraps
from flask import Flask, jsonify, request, g
from werkzeug.exceptions import HTTPException
from .db import Base
from .servicio import Restaurante
from .errores import ErrorNegocio, ErrorBase, exigir
from .datos_iniciales import cargar_catalogo


def crear_app(base=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=65536, JSON_SORT_KEYS=False)
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    base = base or Base()
    base.inicializar()
    servicio = Restaurante(base)
    app.extensions["restaurante"] = servicio

    def respuesta(datos, estado=200):
        return jsonify({"ok": True, "datos": datos}), estado

    def datos(requeridos=None, opcionales=None):
        requeridos, opcionales = requeridos or {}, opcionales or {}
        if not request.is_json:
            raise ErrorNegocio(
                "TIPO_CONTENIDO",
                "Usa Body > raw > JSON y Content-Type: application/json.",
            )
        d = request.get_json()
        exigir(type(d) is dict, "El cuerpo debe ser un objeto JSON.", "JSON_INVALIDO")
        faltan = set(requeridos) - d.keys()
        exigir(not faltan, "Faltan campos: " + ", ".join(sorted(faltan)))
        extras = d.keys() - (requeridos.keys() | opcionales.keys())
        exigir(not extras, "Campos desconocidos: " + ", ".join(sorted(extras)))
        for k, tipo in (requeridos | opcionales).items():
            if k in d:
                tipos = tipo if isinstance(tipo, tuple) else (tipo,)
                exigir(type(d[k]) in tipos, f"{k}: tipo de dato incorrecto.")
        return d

    def proteger(roles=None, cambio=False):
        def decorar(funcion):
            @wraps(funcion)
            def envuelta(*args, **kwargs):
                auth = request.headers.get("Authorization", "").split()
                exigir(
                    len(auth) == 2 and auth[0].lower() == "bearer",
                    "Envía Authorization: Bearer <token>.",
                    "SESION",
                )
                g.token = auth[1]
                # El servicio vuelve a verificar permisos dentro de cada transacción.
                with base.transaccion() as c:
                    g.usuario = servicio._actor(
                        c,
                        g.token,
                        roles or ("ADMINISTRADOR", "MESERO", "COCINA"),
                        permite_cambio=cambio,
                    )
                return funcion(*args, **kwargs)

            return envuelta

        return decorar

    def clave_operacion():
        clave = request.headers.get("Idempotency-Key")
        exigir(
            bool(clave),
            "Envía Idempotency-Key: una UUID minúscula. Conserva la clave al reintentar.",
        )
        return clave

    def numero_query(nombre, defecto=1):
        raw = request.args.get(nombre)
        if raw is None:
            return defecto
        exigir(
            raw.isascii() and raw.isdigit(), f"{nombre}: se requiere entero positivo."
        )
        n = int(raw)
        exigir(1 <= n <= 1000000, f"{nombre}: fuera de rango.")
        return n

    def bool_query(nombre):
        raw = request.args.get(nombre, "false")
        exigir(raw in ("true", "false"), f"{nombre}: usa true o false.")
        return raw == "true"

    def por_id(filas, ident):
        fila = next((x for x in filas if x["id"] == ident), None)
        exigir(
            fila is not None,
            "No existe el recurso solicitado o no está disponible.",
            "NO_EXISTE",
        )
        return fila

    @app.after_request
    def cabeceras(r):
        r.headers["Cache-Control"] = "no-store"
        r.headers["X-Content-Type-Options"] = "nosniff"
        return r

    @app.errorhandler(ErrorNegocio)
    def error_negocio(exc):
        codigos = {
            "SESION": 401,
            "CREDENCIALES": 401,
            "PERMISO": 403,
            "CAMBIAR_CLAVE": 403,
            "NO_EXISTE": 404,
            "CONFLICTO": 409,
            "ESTADO": 409,
            "YA_CONFIGURADO": 409,
            "INTEGRIDAD": 409,
            "BLOQUEADO": 429,
            "TIPO_CONTENIDO": 415,
            "JSON_INVALIDO": 400,
        }
        estado = codigos.get(exc.codigo, 422)
        r = jsonify({"ok": False, "error": {"codigo": exc.codigo, "mensaje": str(exc)}})
        r.status_code = estado
        if estado == 401:
            r.headers["WWW-Authenticate"] = "Bearer"
        if estado == 429:
            r.headers["Retry-After"] = "900"
        return r

    @app.errorhandler(ErrorBase)
    def error_base(exc):
        estado = 409 if getattr(exc, "codigo", "") == "CONFLICTO" else 503
        return (
            jsonify(
                {
                    "ok": False,
                    "error": {
                        "codigo": getattr(exc, "codigo", "BASE"),
                        "mensaje": str(exc),
                    },
                }
            ),
            estado,
        )

    @app.errorhandler(HTTPException)
    def error_http(exc):
        r = exc.get_response()  # Conserva Allow para 405 y demás cabeceras HTTP.
        r.data = app.json.dumps(
            {
                "ok": False,
                "error": {"codigo": f"HTTP_{exc.code}", "mensaje": exc.description},
            }
        )
        r.content_type = "application/json"
        return r

    @app.errorhandler(Exception)
    def error_inesperado(exc):
        app.logger.exception("Fallo inesperado en la API")
        return (
            jsonify(
                {
                    "ok": False,
                    "error": {
                        "codigo": "INTERNO",
                        "mensaje": "No se confirmó la operación. Conserva su clave y consulta antes de reintentar.",
                    },
                }
            ),
            500,
        )

    @app.get("/api/v1/salud")
    def salud():
        base.verificar_esquema()
        return respuesta(
            {"servicio": "PoliRestaurante API", "version": 1, "motor": base.motor}
        )

    @app.post("/api/v1/auth/login")
    def login():
        d = datos({"login": str, "password": str})
        token = servicio.iniciar_sesion(**d)
        return respuesta(
            {
                "token": token,
                "tipo": "Bearer",
                "expira_en_segundos": 28800,
                "usuario": servicio.perfil(token),
            }
        )

    @app.get("/api/v1/auth/me")
    @proteger(cambio=True)
    def perfil():
        return respuesta(servicio.perfil(g.token))

    @app.post("/api/v1/auth/logout")
    @proteger(cambio=True)
    def logout():
        servicio.cerrar_sesion(g.token)
        return respuesta({"mensaje": "Sesión cerrada."})

    @app.put("/api/v1/auth/password")
    @proteger(cambio=True)
    def password():
        d = datos({"actual": str, "nueva": str})
        servicio.cambiar_clave(g.token, **d)
        return respuesta(
            {
                "mensaje": "Contraseña cambiada. Inicia sesión nuevamente; el token anterior fue revocado."
            }
        )

    @app.post("/api/v1/admin/datos-iniciales")
    @proteger(("ADMINISTRADOR",))
    def iniciales():
        datos()
        return respuesta(cargar_catalogo(servicio, g.token))

    @app.get("/api/v1/usuarios")
    @proteger(("ADMINISTRADOR",))
    def usuarios():
        return respuesta(servicio.listar_usuarios(g.token))

    @app.get("/api/v1/usuarios/<int:ident>")
    @proteger(("ADMINISTRADOR",))
    def usuario(ident):
        return respuesta(por_id(servicio.listar_usuarios(g.token), ident))

    @app.route("/api/v1/usuarios", methods=["POST"])
    @app.route("/api/v1/usuarios/<int:ident>", methods=["PUT"])
    @proteger(("ADMINISTRADOR",))
    def guardar_usuario(ident=None):
        d = datos(
            {"nombre": str, "login": str, "rol": str}, {"activo": bool, "password": str}
        )
        return respuesta(
            servicio.guardar_usuario(g.token, **d, uid=ident),
            201 if ident is None else 200,
        )

    @app.delete("/api/v1/usuarios/<int:ident>")
    @proteger(("ADMINISTRADOR",))
    def borrar_usuario(ident):
        return respuesta(servicio.desactivar_usuario(g.token, ident))

    @app.get("/api/v1/categorias")
    @proteger()
    def categorias():
        return respuesta(servicio.categorias(g.token))

    @app.get("/api/v1/categorias/<int:ident>")
    @proteger()
    def categoria(ident):
        return respuesta(por_id(servicio.categorias(g.token), ident))

    @app.route("/api/v1/categorias", methods=["POST"])
    @app.route("/api/v1/categorias/<int:ident>", methods=["PUT"])
    @proteger(("ADMINISTRADOR",))
    def guardar_categoria(ident=None):
        d = datos({"nombre": str})
        return respuesta(
            servicio.guardar_categoria(g.token, d["nombre"], ident),
            201 if ident is None else 200,
        )

    @app.delete("/api/v1/categorias/<int:ident>")
    @proteger(("ADMINISTRADOR",))
    def borrar_categoria(ident):
        return respuesta(servicio.eliminar_categoria(g.token, ident))

    @app.get("/api/v1/productos")
    @proteger()
    def productos():
        return respuesta(servicio.productos(g.token, bool_query("incluir_archivados")))

    @app.get("/api/v1/productos/<int:ident>")
    @proteger()
    def producto(ident):
        return respuesta(por_id(servicio.productos(g.token, True), ident))

    @app.route("/api/v1/productos", methods=["POST"])
    @app.route("/api/v1/productos/<int:ident>", methods=["PUT"])
    @proteger(("ADMINISTRADOR",))
    def guardar_producto(ident=None):
        d = datos(
            {"nombre": str, "descripcion": str, "precio": str, "categoria_id": int},
            {"disponible": bool, "activo": bool},
        )
        return respuesta(
            servicio.guardar_producto(g.token, **d, pid=ident),
            201 if ident is None else 200,
        )

    @app.delete("/api/v1/productos/<int:ident>")
    @proteger(("ADMINISTRADOR",))
    def borrar_producto(ident):
        return respuesta(servicio.archivar_producto(g.token, ident))

    @app.get("/api/v1/mesas")
    @proteger()
    def mesas():
        return respuesta(servicio.mesas(g.token, bool_query("incluir_archivadas")))

    @app.get("/api/v1/mesas/<int:ident>")
    @proteger()
    def mesa(ident):
        return respuesta(por_id(servicio.mesas(g.token, True), ident))

    @app.route("/api/v1/mesas", methods=["POST"])
    @app.route("/api/v1/mesas/<int:ident>", methods=["PUT"])
    @proteger(("ADMINISTRADOR",))
    def guardar_mesa(ident=None):
        d = datos({"numero": int, "capacidad": int}, {"activa": bool})
        return respuesta(
            servicio.guardar_mesa(g.token, **d, mid=ident),
            201 if ident is None else 200,
        )

    @app.delete("/api/v1/mesas/<int:ident>")
    @proteger(("ADMINISTRADOR",))
    def borrar_mesa(ident):
        return respuesta(servicio.archivar_mesa(g.token, ident))

    @app.get("/api/v1/pedidos")
    @proteger()
    def pedidos():
        return respuesta(
            servicio.listar_pedidos(
                g.token,
                request.args.get("estado"),
                bool_query("abiertos"),
                numero_query("pagina"),
            )
        )

    @app.get("/api/v1/cocina/cola")
    @proteger(("ADMINISTRADOR", "COCINA"))
    def cola():
        return respuesta(servicio.cola_cocina(g.token, numero_query("pagina")))

    @app.get("/api/v1/pedidos/<int:pid>")
    @proteger()
    def pedido(pid):
        return respuesta(servicio.obtener_pedido(g.token, pid))

    @app.post("/api/v1/pedidos")
    @proteger(("ADMINISTRADOR", "MESERO"))
    def crear_pedido():
        d = datos(
            {"tipo": str},
            {"mesa_id": (int, type(None)), "responsable_id": (int, type(None))},
        )
        return respuesta(
            servicio.crear_pedido(g.token, **d, clave=clave_operacion()), 201
        )

    @app.post("/api/v1/pedidos/<int:pid>/detalles")
    @proteger(("ADMINISTRADOR", "MESERO"))
    def agregar(pid):
        d = datos({"producto_id": int, "cantidad": int, "version": int}, {"notas": str})
        d.setdefault("notas", "")
        return respuesta(
            servicio.agregar_producto(g.token, pid, **d, clave=clave_operacion()), 201
        )

    @app.put("/api/v1/pedidos/<int:pid>/detalles/<int:did>")
    @proteger(("ADMINISTRADOR", "MESERO"))
    def editar(pid, did):
        d = datos({"cantidad": int, "notas": str, "version": int})
        return respuesta(
            servicio.editar_detalle(g.token, pid, did, **d, clave=clave_operacion())
        )

    @app.delete("/api/v1/pedidos/<int:pid>/detalles/<int:did>")
    @proteger(("ADMINISTRADOR", "MESERO"))
    def quitar(pid, did):
        # DELETE usa query para la versión: no depende de soportar un cuerpo DELETE.
        return respuesta(
            servicio.quitar_detalle(
                g.token, pid, did, numero_query("version", None), clave_operacion()
            )
        )

    @app.patch("/api/v1/pedidos/<int:pid>/estado")
    @proteger()
    def estado(pid):
        d = datos({"estado": str, "version": int}, {"motivo": str})
        d["nuevo"] = d.pop("estado")
        return respuesta(
            servicio.cambiar_estado(g.token, pid, **d, clave=clave_operacion())
        )

    @app.patch("/api/v1/pedidos/<int:pid>/asignacion")
    @proteger(("ADMINISTRADOR",))
    def asignacion(pid):
        d = datos(
            {"version": int, "motivo": str},
            {"responsable_id": (int, type(None)), "cocinero_id": (int, type(None))},
        )
        d.setdefault("responsable_id", None)
        d.setdefault("cocinero_id", None)
        return respuesta(
            servicio.reasignar_pedido(g.token, pid, **d, clave=clave_operacion())
        )

    @app.get("/api/v1/operaciones/<clave>")
    @proteger()
    def operacion(clave):
        return respuesta(servicio.consultar_operacion(g.token, clave))

    @app.get("/api/v1/reportes/ventas")
    @proteger(("ADMINISTRADOR",))
    def ventas():
        return respuesta(
            servicio.ventas(
                g.token,
                request.args.get("desde"),
                request.args.get("hasta"),
                numero_query("categoria_id", None),
                numero_query("producto_id", None),
            )
        )

    @app.get("/api/v1/reportes/tiempos")
    @proteger(("ADMINISTRADOR",))
    def tiempos():
        return respuesta(
            servicio.tiempos(
                g.token, request.args.get("desde"), request.args.get("hasta")
            )
        )

    @app.get("/api/v1/admin/auditoria")
    @proteger(("ADMINISTRADOR",))
    def auditoria():
        return respuesta(servicio.auditoria(g.token, numero_query("pagina")))

    @app.get("/api/v1/admin/tablas/<tabla>")
    @proteger(("ADMINISTRADOR",))
    def tablas(tabla):
        return respuesta(servicio.inspeccionar(g.token, tabla, numero_query("pagina")))

    return app
