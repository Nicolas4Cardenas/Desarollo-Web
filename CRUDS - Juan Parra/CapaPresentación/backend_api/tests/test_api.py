"""Integración HTTP del adaptador Flask con bases temporales."""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from poli.api import crear_app
from poli.db import Base
from poli.servicio import Restaurante
from poli.errores import ErrorBase

ADMIN = "Administrador123!"
TEMP = "TemporalSegura123!"
PROPIA = "PersonalSegura123!"


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Base(ruta=Path(self.tmp.name) / "api.db")
        self.base.inicializar()
        self.s = Restaurante(self.base)
        self.s.crear_primer_admin("Dueño", "admin", ADMIN)
        self.app = crear_app(self.base)
        self.c = self.app.test_client()
        self.a = self.login("admin", ADMIN)

    def call(self, method, path, token=None, body=None, key=None, expected=200):
        h = {"Authorization": "Bearer " + token} if token else {}
        if key:
            h["Idempotency-Key"] = key
        r = self.c.open("/api/v1" + path, method=method, json=body, headers=h)
        self.assertEqual(r.status_code, expected, r.json)
        self.assertEqual(r.json["ok"], expected < 400, r.json)
        return r.json.get("datos", r.json.get("error"))

    def login(self, login, password):
        return self.call(
            "POST", "/auth/login", body={"login": login, "password": password}
        )["token"]

    def empleado(self, login, rol):
        d = self.call(
            "POST",
            "/usuarios",
            self.a,
            {"nombre": login, "login": login, "rol": rol, "password": TEMP},
            expected=201,
        )
        t = self.login(login, TEMP)
        self.call("PUT", "/auth/password", t, {"actual": TEMP, "nueva": PROPIA})
        return d["id"], self.login(login, PROPIA)

    def catalogo(self):
        self.call("POST", "/admin/datos-iniciales", self.a, {})
        return (
            self.call("GET", "/productos", self.a)[0]["id"],
            self.call("GET", "/mesas", self.a)[0]["id"],
        )

    def crear(self, tipo="LLEVAR", mesa=None, token=None):
        d = {"tipo": tipo}
        if mesa:
            d["mesa_id"] = mesa
        return self.call("POST", "/pedidos", token or self.a, d, str(uuid4()), 201)

    def test_01_salud_y_proteccion(self):
        self.assertEqual(self.call("GET", "/salud")["motor"], "sqlite")
        for path in (
            "/usuarios",
            "/pedidos",
            "/productos",
            "/mesas",
            "/admin/auditoria",
        ):
            self.call("GET", path, expected=401)
        r = self.c.get("/api/v1/usuarios")
        self.assertEqual(r.headers["WWW-Authenticate"], "Bearer")
        self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_02_json_malformado_y_tipos(self):
        h = {"Authorization": "Bearer " + self.a, "Content-Type": "application/json"}
        for raw, code in (
            ("{", 400),
            ("[]", 400),
            ("null", 400),
            ('"texto"', 400),
            ('{"nombre":true}', 422),
            ('{"nombre":"X","intruso":1}', 422),
        ):
            r = self.c.post("/api/v1/categorias", data=raw, headers=h)
            self.assertEqual(r.status_code, code, r.json)
            self.assertFalse(r.json["ok"])
        self.assertEqual(
            self.c.post("/api/v1/auth/login", data="hola").status_code, 415
        )
        self.assertEqual(
            self.c.post("/api/v1/auth/login", data="x" * 70000, headers=h).status_code,
            413,
        )
        for numero in (True, "2", None, 2.5):
            self.call(
                "POST",
                "/mesas",
                self.a,
                {"numero": numero, "capacidad": 4},
                expected=422,
            )
        self.call(
            "POST",
            "/usuarios",
            self.a,
            {"nombre": "X", "login": "usuario", "rol": ["MESERO"], "password": TEMP},
            expected=422,
        )

    def test_03_login_cambio_y_logout(self):
        self.call(
            "POST",
            "/auth/login",
            body={"login": "admin", "password": "incorrecta"},
            expected=401,
        )
        self.call(
            "POST",
            "/usuarios",
            self.a,
            {"nombre": "Juan", "login": "juan", "rol": "MESERO", "password": TEMP},
            expected=201,
        )
        t = self.login("juan", TEMP)
        self.assertTrue(self.call("GET", "/auth/me", t)["debe_cambiar"])
        self.call("GET", "/productos", t, expected=403)
        self.call("PUT", "/auth/password", t, {"actual": TEMP, "nueva": PROPIA})
        self.call("GET", "/auth/me", t, expected=401)
        t = self.login("juan", PROPIA)
        self.call("POST", "/auth/logout", t)
        self.call("GET", "/auth/me", t, expected=401)

    def test_04_roles(self):
        _, m = self.empleado("mesero", "MESERO")
        _, k = self.empleado("cocina", "COCINA")
        self.call("POST", "/categorias", m, {"nombre": "Prohibida"}, expected=403)
        self.call("GET", "/usuarios", k, expected=403)
        self.call("POST", "/pedidos", k, {"tipo": "LLEVAR"}, str(uuid4()), 403)
        self.call("GET", "/cocina/cola", m, expected=403)
        self.call("POST", "/admin/datos-iniciales", m, {}, expected=403)
        for t in (m, k):
            for path in ("/productos", "/mesas", "/categorias"):
                self.call("GET", path, t)

    def test_05_carga_inicial_atomica_y_unica(self):
        with patch.object(
            Restaurante, "_auditar", side_effect=RuntimeError("Fallo simulado")
        ):
            with self.assertLogs(self.app.logger, level="ERROR"):
                self.call("POST", "/admin/datos-iniciales", self.a, {}, expected=500)
        self.assertEqual(self.call("GET", "/productos", self.a), [])
        d = self.call("POST", "/admin/datos-iniciales", self.a, {})
        self.assertEqual(d["creados"], {"categorias": 4, "productos": 10, "mesas": 6})
        c = self.call("GET", "/categorias", self.a)[0]
        self.call(
            "PUT", f'/categorias/{c["id"]}', self.a, {"nombre": "Nombre del dueño"}
        )
        self.assertFalse(
            self.call("POST", "/admin/datos-iniciales", self.a, {})["cargado"]
        )
        for path, n in (("/categorias", 4), ("/productos", 10), ("/mesas", 6)):
            self.assertEqual(len(self.call("GET", path, self.a)), n)
        self.assertEqual(
            self.call("GET", f'/categorias/{c["id"]}', self.a)["nombre"],
            "Nombre del dueño",
        )

    def test_06_crud_catalogo(self):
        cid = self.call(
            "POST", "/categorias", self.a, {"nombre": "Comida"}, expected=201
        )["id"]
        self.call("GET", f"/categorias/{cid}", self.a)
        self.call("PUT", f"/categorias/{cid}", self.a, {"nombre": "Comidas"})
        self.call("POST", "/categorias", self.a, {"nombre": "Comidas"}, expected=409)
        prod = {
            "nombre": "Arroz",
            "descripcion": "Porción",
            "precio": "12500.50",
            "categoria_id": cid,
        }
        pid = self.call("POST", "/productos", self.a, prod, expected=201)["id"]
        self.assertEqual(
            self.call("GET", f"/productos/{pid}", self.a)["precio_centavos"], 1250050
        )
        self.call("DELETE", f"/categorias/{cid}", self.a, expected=409)
        prod["precio"] = "14000.00"
        self.call("PUT", f"/productos/{pid}", self.a, prod)
        self.call("DELETE", f"/productos/{pid}", self.a)
        self.assertEqual(self.call("GET", "/productos", self.a), [])
        self.assertEqual(
            len(self.call("GET", "/productos?incluir_archivados=true", self.a)), 1
        )
        self.call("DELETE", "/categorias/9999", self.a, expected=404)
        vacia = self.call(
            "POST", "/categorias", self.a, {"nombre": "Vacía"}, expected=201
        )["id"]
        self.call("DELETE", f"/categorias/{vacia}", self.a)
        self.call("GET", f"/categorias/{vacia}", self.a, expected=404)

    def test_07_crud_mesas_usuarios(self):
        mid = self.call(
            "POST", "/mesas", self.a, {"numero": 10, "capacidad": 4}, expected=201
        )["id"]
        self.call("PUT", f"/mesas/{mid}", self.a, {"numero": 10, "capacidad": 6})
        self.assertEqual(self.call("GET", f"/mesas/{mid}", self.a)["capacidad"], 6)
        self.call("DELETE", f"/mesas/{mid}", self.a)
        self.assertEqual(self.call("GET", "/mesas", self.a), [])
        uid, _ = self.empleado("auxiliar", "MESERO")
        self.call("GET", f"/usuarios/{uid}", self.a)
        self.call(
            "PUT",
            f"/usuarios/{uid}",
            self.a,
            {"nombre": "Aux", "login": "auxiliar", "rol": "COCINA"},
        )
        self.call("DELETE", f"/usuarios/{uid}", self.a)
        self.call(
            "POST",
            "/auth/login",
            body={"login": "auxiliar", "password": PROPIA},
            expected=401,
        )
        self.assertNotIn("password_hash", str(self.call("GET", "/usuarios", self.a)))

    def test_08_ciclo_completo_de_juan(self):
        prod, mesa = self.catalogo()
        _, m = self.empleado("mesero", "MESERO")
        _, k = self.empleado("cocina", "COCINA")
        p = self.crear("SALON", mesa, m)
        pid = p["id"]
        self.call(
            "POST", "/pedidos", m, {"tipo": "SALON", "mesa_id": mesa}, str(uuid4()), 409
        )
        self.call(
            "PATCH",
            f"/pedidos/{pid}/estado",
            k,
            {"estado": "EN_PREPARACION", "version": p["version"]},
            str(uuid4()),
            409,
        )
        p = self.call(
            "POST",
            f"/pedidos/{pid}/detalles",
            m,
            {"producto_id": prod, "cantidad": 2, "version": p["version"]},
            str(uuid4()),
            201,
        )
        d = self.call("GET", f"/pedidos/{pid}", m)["detalles"][0]["id"]
        p = self.call(
            "PUT",
            f"/pedidos/{pid}/detalles/{d}",
            m,
            {"cantidad": 3, "notas": "Sin sal", "version": p["version"]},
            str(uuid4()),
        )
        p = self.call(
            "DELETE",
            f'/pedidos/{pid}/detalles/{d}?version={p["version"]}',
            m,
            key=str(uuid4()),
        )
        p = self.call(
            "POST",
            f"/pedidos/{pid}/detalles",
            m,
            {"producto_id": prod, "cantidad": 1, "version": p["version"]},
            str(uuid4()),
            201,
        )
        self.assertEqual(self.call("GET", "/cocina/cola", k)["items"][0]["id"], pid)
        for e, t in (("EN_PREPARACION", k), ("LISTO", k), ("ENTREGADO", m)):
            p = self.call(
                "PATCH",
                f"/pedidos/{pid}/estado",
                t,
                {"estado": e, "version": p["version"]},
                str(uuid4()),
            )
        self.assertEqual(len(self.call("GET", f"/pedidos/{pid}", m)["historial"]), 4)
        self.assertEqual(self.call("GET", f"/mesas/{mesa}", m)["estado"], "LIBRE")

    def test_09_idempotencia_version_propiedad(self):
        _, m = self.empleado("mesero", "MESERO")
        _, otro = self.empleado("otro", "MESERO")
        key = str(uuid4())
        p = self.call("POST", "/pedidos", m, {"tipo": "LLEVAR"}, key, 201)
        self.assertEqual(
            p, self.call("POST", "/pedidos", m, {"tipo": "LLEVAR"}, key, 201)
        )
        self.assertEqual(self.call("GET", "/operaciones/" + key, m)["resultado"], p)
        self.call("GET", "/operaciones/" + key, otro, expected=404)
        self.call("GET", f'/pedidos/{p["id"]}', otro, expected=403)
        self.assertEqual(self.call("GET", "/pedidos", otro)["items"], [])
        self.call("POST", "/pedidos", m, {"tipo": "SALON", "mesa_id": 1}, key, 409)
        prod, _ = self.catalogo()
        self.call(
            "POST",
            f'/pedidos/{p["id"]}/detalles',
            m,
            {"producto_id": prod, "cantidad": 1, "version": 1},
            str(uuid4()),
            201,
        )
        self.call(
            "POST",
            f'/pedidos/{p["id"]}/detalles',
            m,
            {"producto_id": prod, "cantidad": 1, "version": 1},
            str(uuid4()),
            409,
        )
        self.call("POST", "/pedidos", m, {"tipo": "LLEVAR"}, expected=422)
        self.call("POST", "/pedidos", m, {"tipo": "LLEVAR"}, "invalida", 422)

    def test_10_cancelar_reasignar_reportes(self):
        hoy = datetime.now(timezone.utc).date().isoformat()
        uid, m = self.empleado("mesero", "MESERO")
        _, mesa = self.catalogo()
        p = self.crear("SALON", mesa, m)
        self.call(
            "PATCH",
            f'/pedidos/{p["id"]}/estado',
            m,
            {"estado": "CANCELADO", "version": 1},
            str(uuid4()),
            422,
        )
        self.call(
            "PATCH",
            f'/pedidos/{p["id"]}/estado',
            m,
            {"estado": "CANCELADO", "version": 1, "motivo": "Cliente se retira"},
            str(uuid4()),
        )
        self.assertEqual(self.call("GET", f"/mesas/{mesa}", self.a)["estado"], "LIBRE")
        p = self.crear()
        self.call(
            "PATCH",
            f'/pedidos/{p["id"]}/asignacion',
            self.a,
            {"responsable_id": uid, "version": 1, "motivo": "Turno"},
            str(uuid4()),
        )
        self.call("GET", f'/pedidos/{p["id"]}', m)
        for path in (
            f"/reportes/ventas?desde={hoy}&hasta={hoy}",
            f"/reportes/tiempos?desde={hoy}&hasta={hoy}",
        ):
            self.call("GET", path, self.a)
            self.call("GET", path, m, expected=403)
        self.assertEqual(
            self.call("GET", f"/reportes/ventas?desde={hoy}&hasta={hoy}", self.a)[
                "pedidos"
            ],
            0,
        )
        self.call("GET", "/reportes/ventas", self.a, expected=422)
        self.call("GET", "/admin/auditoria", self.a)
        self.assertNotIn(
            "password_hash", str(self.call("GET", "/admin/tablas/usuario", self.a))
        )
        self.call("GET", "/admin/tablas/sesion", self.a, expected=422)
        self.call("GET", "/admin/tablas/pedido", m, expected=403)

    def test_11_http_queries_errores(self):
        self.call("GET", "/no-existe", expected=404)
        r = self.c.put("/api/v1/salud")
        self.assertEqual(r.status_code, 405)
        self.assertIn("GET", r.headers["Allow"])
        for path in (
            "/pedidos?pagina=0",
            "/pedidos?pagina=true",
            "/pedidos?pagina=-2",
            "/pedidos?pagina=1.2",
            "/pedidos?abiertos=si",
            "/mesas?incluir_archivadas=1",
            "/productos?incluir_archivados=x",
        ):
            self.call("GET", path, self.a, expected=422)
        self.call("GET", "/pedidos/99999", self.a, expected=404)
        self.call("GET", "/pedidos?pagina=2", self.a)
        with patch.object(
            Restaurante,
            "listar_usuarios",
            side_effect=ErrorBase("Servidor no disponible"),
        ):
            self.call("GET", "/usuarios", self.a, expected=503)

    def test_12_bloqueo_login(self):
        for _ in range(5):
            self.call(
                "POST",
                "/auth/login",
                body={"login": "admin", "password": "incorrecta"},
                expected=401,
            )
        self.assertEqual(
            self.call(
                "POST",
                "/auth/login",
                body={"login": "admin", "password": ADMIN},
                expected=429,
            )["codigo"],
            "BLOQUEADO",
        )


if __name__ == "__main__":
    unittest.main()
