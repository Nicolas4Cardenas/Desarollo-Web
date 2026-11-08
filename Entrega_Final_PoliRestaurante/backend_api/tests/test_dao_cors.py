"""Prueba observable de HU02 con tres DAO reales y preflight de Live Server."""

from tempfile import TemporaryDirectory
from pathlib import Path
from uuid import uuid4
from unittest import TestCase
from unittest.mock import patch
from poli.api import crear_app
from poli.db import Base
from poli.servicio import Restaurante
from poli.dao import DetalleDAO, PedidoDAO, ProductoDAO
from poli.errores import ErrorNegocio


class DaoCorsTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.b = Base(ruta=Path(self.tmp.name) / "dao.db")
        self.b.inicializar()
        self.s = Restaurante(self.b)
        self.s.crear_primer_admin("Dueño", "admin", "Presentacion123!")
        self.t = self.s.iniciar_sesion("admin", "Presentacion123!")
        self.cat = self.s.guardar_categoria(self.t, "Comida")["id"]
        self.prod = self.s.guardar_producto(self.t, "Almuerzo", "", "15000", self.cat)[
            "id"
        ]
        self.p = self.s.crear_pedido(self.t, "LLEVAR")
        self.c = crear_app(self.b).test_client()

    def test_tres_dao_reales_comparten_cursor_en_peticion_hu02(self):
        observados = []
        op = PedidoDAO.obtener
        opr = ProductoDAO.obtener
        od = DetalleDAO.crear

        def pedido(dao, ident):
            observados.append(("pedido", dao.cursor))
            return op(dao, ident)

        def producto(dao, ident):
            observados.append(("producto", dao.cursor))
            return opr(dao, ident)

        def detalle(dao, *args):
            observados.append(("detalle", dao.cursor))
            return od(dao, *args)

        with (
            patch.object(PedidoDAO, "obtener", autospec=True, side_effect=pedido),
            patch.object(ProductoDAO, "obtener", autospec=True, side_effect=producto),
            patch.object(DetalleDAO, "crear", autospec=True, side_effect=detalle),
        ):
            r = self.c.post(
                f'/api/v1/pedidos/{self.p["id"]}/detalles',
                json={"producto_id": self.prod, "cantidad": 2, "version": 1},
                headers={
                    "Authorization": "Bearer " + self.t,
                    "Idempotency-Key": str(uuid4()),
                },
            )
        self.assertEqual(r.status_code, 201, r.json)
        self.assertEqual([x[0] for x in observados], ["pedido", "producto", "detalle"])
        self.assertTrue(all(c is observados[0][1] for _, c in observados))
        self.assertEqual(
            self.s.obtener_pedido(self.t, self.p["id"])["total_centavos"], 3000000
        )

    def test_fallo_segundo_dao_no_deja_escritura_parcial(self):
        with patch.object(
            ProductoDAO,
            "obtener",
            side_effect=ErrorNegocio("NO_EXISTE", "No hay producto"),
        ):
            r = self.c.post(
                f'/api/v1/pedidos/{self.p["id"]}/detalles',
                json={"producto_id": self.prod, "cantidad": 2, "version": 1},
                headers={
                    "Authorization": "Bearer " + self.t,
                    "Idempotency-Key": str(uuid4()),
                },
            )
        self.assertEqual(r.status_code, 404)
        p = self.s.obtener_pedido(self.t, self.p["id"])
        self.assertEqual((p["version"], p["detalles"]), (1, []))

    def test_cors_live_server_permite_headers_reales(self):
        for origen in ("http://127.0.0.1:5500", "http://localhost:5500"):
            r = self.c.options(
                "/api/v1/pedidos/1/detalles",
                headers={
                    "Origin": origen,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
                },
            )
            self.assertEqual(r.headers.get("Access-Control-Allow-Origin"), origen)
            self.assertIn(
                "idempotency-key",
                r.headers.get("Access-Control-Allow-Headers", "").lower(),
            )

    def test_cors_no_da_permisos_ni_admite_origen_arbitrario(self):
        r = self.c.get("/api/v1/usuarios", headers={"Origin": "http://localhost:5500"})
        self.assertEqual(r.status_code, 401)
        r = self.c.options(
            "/api/v1/pedidos",
            headers={
                "Origin": "https://ejemplo.invalid",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotIn("Access-Control-Allow-Origin", r.headers)

    def test_archivos_del_cliente_servidos_por_flask(self):
        self.assertEqual(self.c.get("/").status_code, 302)
        for p in (
            "cliente.html",
            "js/app.js",
            "css/styles.css",
            "vendor/bootstrap/bootstrap.min.css",
        ):
            with self.c.get("/cliente/" + p) as r:
                self.assertEqual(r.status_code, 200, p)
