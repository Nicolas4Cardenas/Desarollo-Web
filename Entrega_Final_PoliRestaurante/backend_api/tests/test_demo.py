"""Carga demo: datos relacionados, preservación, repetición y login de todas las cuentas."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from poli.db import Base
from poli.demo import cargar_demo, CUENTAS, texto_credenciales
from poli.servicio import Restaurante
from poli.seguridad import verificar_clave
from poli.errores import ErrorNegocio


class DemoTests(TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.b = Base(ruta=Path(self.tmp.name) / "demo.db")
        self.b.inicializar()
        self.s = Restaurante(self.b)

    def conteo(self, tabla):
        with self.b.transaccion() as c:
            c.execute("SELECT COUNT(*) AS n FROM " + tabla)
            return c.one()["n"]

    def test_todas_las_cuentas_entran_sin_cambio_temporal(self):
        r = cargar_demo(self.b)
        self.assertEqual(
            r["creados"], dict(usuarios=7, categorias=6, productos=20, mesas=12)
        )
        for _, login, rol, password in CUENTAS:
            with self.subTest(login=login):
                t = self.s.iniciar_sesion(login, password)
                u = self.s.perfil(t)
                self.assertEqual((u["rol"], u["debe_cambiar"]), (rol, 0))
                self.s.productos(t)
        with self.b.transaccion() as c:
            c.execute("SELECT login,password_hash FROM usuario")
            hashes = c.all()
        for fila in hashes:
            self.assertNotIn(
                next(x[3] for x in CUENTAS if x[1] == fila["login"]),
                fila["password_hash"],
            )

    def test_conserva_usuarios_pedidos_precios_y_mesas_previos(self):
        self.s.crear_primer_admin("Dueño anterior", "admin", "AnteriorSegura123!")
        a = self.s.iniciar_sesion("admin", "AnteriorSegura123!")
        cid = self.s.guardar_categoria(a, "Bebidas")["id"]
        pid = self.s.guardar_producto(a, "Agua", "Precio del dueño", "9100", cid)["id"]
        mid = self.s.guardar_mesa(a, 1, 10)["id"]
        p = self.s.crear_pedido(a, "SALON", mid)
        with self.b.transaccion() as c:
            c.execute("SELECT * FROM usuario WHERE login=?", ("admin",))
            original = c.one()
        cargar_demo(self.b)
        with self.b.transaccion() as c:
            c.execute("SELECT * FROM usuario WHERE login=?", ("admin",))
            self.assertEqual(c.one(), original)
        agua = next(x for x in self.s.productos(a) if x["id"] == pid)
        self.assertEqual(agua["precio_centavos"], 910000)
        mesa = next(x for x in self.s.mesas(a) if x["id"] == mid)
        self.assertEqual((mesa["capacidad"], mesa["pedido_id"]), (10, p["id"]))
        self.assertEqual(self.s.obtener_pedido(a, p["id"])["version"], 1)

    def test_repetir_no_duplica_ni_cambia_hashes_o_claves(self):
        cargar_demo(self.b)
        a = self.s.iniciar_sesion("admin.demo", "AdminClase2026!")
        t = self.s.iniciar_sesion("juan.demo", "MeseroClase2026!")
        self.s.cambiar_clave(t, "MeseroClase2026!", "PersonalNueva123!")
        with self.b.transaccion() as c:
            c.execute("SELECT id,password_hash FROM usuario ORDER BY id")
            antes = c.all()
        r = cargar_demo(self.b)
        self.assertFalse(r["cargado"])
        self.assertTrue(all(v == 0 for v in r["creados"].values()))
        with self.b.transaccion() as c:
            c.execute("SELECT id,password_hash FROM usuario ORDER BY id")
            self.assertEqual(c.all(), antes)
        self.assertEqual(
            [self.conteo(x) for x in ("usuario", "producto", "mesa", "categoria")],
            [7, 20, 12, 6],
        )
        self.s.iniciar_sesion("juan.demo", "PersonalNueva123!")
        self.s.perfil(a)

    def test_restaurar_solo_demo_desbloquea_y_revoca_sesion(self):
        self.s.crear_primer_admin("Anterior", "admin", "AnteriorSegura123!")
        anterior = self.s.iniciar_sesion("admin", "AnteriorSegura123!")
        cargar_demo(self.b)
        demo = self.s.iniciar_sesion("juan.demo", "MeseroClase2026!")
        for _ in range(5):
            with self.assertRaises(ErrorNegocio):
                self.s.iniciar_sesion("juan.demo", "incorrecta")
        with self.assertRaises(ErrorNegocio):
            self.s.iniciar_sesion("juan.demo", "MeseroClase2026!")
        self.assertTrue(cargar_demo(self.b, True)["claves_restablecidas"])
        with self.assertRaises(ErrorNegocio):
            self.s.perfil(demo)
        self.s.iniciar_sesion("juan.demo", "MeseroClase2026!")
        self.s.perfil(anterior)

    def test_colision_de_login_no_reasigna_ni_cambia_datos(self):
        self.s.crear_primer_admin("Cuenta existente", "juan.demo", "ConocidaSegura123!")
        with self.assertRaisesRegex(ErrorNegocio, "Ya existe juan.demo"):
            cargar_demo(self.b)
        self.assertEqual(self.conteo("usuario"), 1)
        self.assertEqual(self.conteo("producto"), 0)
        t = self.s.iniciar_sesion("juan.demo", "ConocidaSegura123!")
        self.assertEqual(self.s.perfil(t)["rol"], "ADMINISTRADOR")

    def test_fallo_en_auditoria_revierte_carga_completa(self):
        with patch.object(
            Restaurante, "_auditar", side_effect=RuntimeError("Fallo simulado")
        ):
            with self.assertRaises(RuntimeError):
                cargar_demo(self.b)
        for tabla in ("usuario", "categoria", "producto", "mesa", "auditoria"):
            self.assertEqual(self.conteo(tabla), 0)

    def test_archivo_credenciales_coincide_con_los_datos(self):
        texto = texto_credenciales()
        for nombre, login, rol, password in CUENTAS:
            for valor in (nombre, login, rol, password):
                self.assertIn(valor, texto)
        archivo = Path(__file__).resolve().parents[2] / "CREDENCIALES_DEMO.txt"
        self.assertEqual(archivo.read_text(encoding="utf-8-sig"), texto)

    def test_ciclo_juan_cocina_de_la_carga(self):
        cargar_demo(self.b)
        j = self.s.iniciar_sesion("juan.demo", "MeseroClase2026!")
        k = self.s.iniciar_sesion("cocina1.demo", "CocinaClase2026!")
        producto = self.s.productos(j)[0]["id"]
        mesa = self.s.mesas(j)[0]["id"]
        p = self.s.crear_pedido(j, "SALON", mesa)
        p = self.s.agregar_producto(j, p["id"], producto, 2, "Sin sal", p["version"])
        for e, t in [("EN_PREPARACION", k), ("LISTO", k), ("ENTREGADO", j)]:
            p = self.s.cambiar_estado(t, p["id"], e, p["version"])
        self.assertEqual(self.s.obtener_pedido(j, p["id"])["estado"], "ENTREGADO")
        self.assertEqual(self.s.mesas(j)[0]["estado"], "LIBRE")
