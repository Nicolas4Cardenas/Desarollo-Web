"""unittest con bases temporales; nunca toca datos de la presentación."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
import sqlite3
import unittest
from unittest.mock import patch
from poli.db import Base
from poli.servicio import Restaurante
from poli.errores import ErrorNegocio, ErrorBase
from poli.seguridad import hash_clave, verificar_clave
from poli import validaciones as v

ADMIN = "AdminSegura123!"
TEMP = "TemporalSegura123!"
PROPIA = "PersonalSegura123!"


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.b = Base(ruta=Path(self.tmp.name) / "datos.db")
        self.b.inicializar()
        self.s = Restaurante(self.b)
        self.aid = self.s.crear_primer_admin("Dueño", "admin", ADMIN)
        self.a = self.s.iniciar_sesion("admin", ADMIN)
        self.jid, self.j = self.usuario("Juan Parra", "juan", "MESERO")
        self.oid, self.o = self.usuario("Otro mesero", "otro", "MESERO")
        self.kid, self.k = self.usuario("Cocina uno", "cocina1", "COCINA")
        self.k2id, self.k2 = self.usuario("Cocina dos", "cocina2", "COCINA")
        self.cid = self.s.guardar_categoria(self.a, "Comidas")["id"]
        self.pid = self.s.guardar_producto(
            self.a, "Hamburguesa", "De la casa", "18500.00", self.cid
        )["id"]
        self.mid = self.s.guardar_mesa(self.a, 1, 4)["id"]

    def usuario(self, nombre, login, rol):
        uid = self.s.guardar_usuario(self.a, nombre, login, rol, password=TEMP)["id"]
        token = self.s.iniciar_sesion(login, TEMP)
        self.s.cambiar_clave(token, TEMP, PROPIA)
        return uid, self.s.iniciar_sesion(login, PROPIA)

    def crear(self, mesa=True, actor=None):
        r = self.s.crear_pedido(
            actor or self.j,
            "SALON" if mesa else "LLEVAR",
            self.mid if mesa else None,
            clave=str(uuid4()),
        )
        return self.s.obtener_pedido(actor or self.j, r["id"])

    def agregar(self, p, actor=None, cantidad=2):
        self.s.agregar_producto(
            actor or self.j,
            p["id"],
            self.pid,
            cantidad,
            "Sin cebolla",
            p["version"],
            str(uuid4()),
        )
        return self.s.obtener_pedido(actor or self.j, p["id"])

    def estado(self, p, estado, actor, motivo=""):
        self.s.cambiar_estado(
            actor, p["id"], estado, p["version"], motivo, str(uuid4())
        )
        return self.s.obtener_pedido(actor, p["id"])

    def test_01_instalacion_vacia(self):
        b = Base(ruta=Path(self.tmp.name) / "limpia.db")
        b.inicializar()
        s = Restaurante(b)
        self.assertTrue(s.necesita_admin())
        with b.transaccion() as c:
            for t in ["usuario", "mesa", "producto", "categoria", "pedido", "detalle"]:
                c.execute("SELECT COUNT(*) AS n FROM " + t)
                self.assertEqual(c.one()["n"], 0)
        s.crear_primer_admin("Dueño", "dueno", ADMIN)
        with self.assertRaises(ErrorNegocio):
            s.crear_primer_admin("Intruso", "otro", ADMIN)

    def test_02_ciclo_y_reportes(self):
        p = self.agregar(self.crear())
        self.assertEqual(p["total_centavos"], 3700000)
        with self.assertRaises(ErrorNegocio):
            self.estado(p, "ENTREGADO", self.j)
        p = self.estado(p, "EN_PREPARACION", self.k)
        p = self.estado(p, "LISTO", self.k)
        p = self.estado(p, "ENTREGADO", self.j)
        self.assertEqual([h["estado"] for h in p["historial"]], list(v.ESTADOS[:4]))
        self.assertEqual(self.s.mesas(self.j)[0]["estado"], "LIBRE")
        hoy = datetime.now(timezone.utc).date().isoformat()
        r = self.s.ventas(self.a, hoy, hoy)
        self.assertEqual(
            (r["total_centavos"], r["unidades"], r["pedidos"]), (3700000, 2, 1)
        )
        self.assertIsNotNone(self.s.tiempos(self.a, hoy, hoy)["promedio_segundos"])
        with self.assertRaises(ErrorNegocio):
            self.estado(p, "CANCELADO", self.a, "Tardío")

    def test_03_editar_quitar_y_vacio(self):
        p = self.agregar(self.crear())
        did = p["detalles"][0]["id"]
        r = self.s.editar_detalle(self.j, p["id"], did, 3, "Sin sal", p["version"])
        self.assertEqual(r["total_centavos"], 5550000)
        r = self.s.quitar_detalle(self.j, p["id"], did, r["version"])
        self.assertEqual(r["total_centavos"], 0)
        with self.assertRaises(ErrorNegocio):
            self.s.cambiar_estado(self.k, p["id"], "EN_PREPARACION", r["version"])

    def test_04_cancelacion_con_trazabilidad(self):
        p = self.estado(self.crear(), "CANCELADO", self.j, "Cliente se retira")
        self.assertEqual(p["historial"][-1]["usuario_id"], self.jid)
        self.assertEqual(p["motivo_cancelacion"], "Cliente se retira")
        p = self.estado(self.agregar(self.crear()), "EN_PREPARACION", self.k)
        self.assertEqual(
            self.estado(p, "CANCELADO", self.j, "Solicitud")["estado"], "CANCELADO"
        )

    def test_05_cancelacion_listo_exclusiva_admin(self):
        p = self.estado(self.agregar(self.crear()), "EN_PREPARACION", self.k)
        p = self.estado(p, "LISTO", self.k)
        with self.assertRaises(ErrorNegocio):
            self.estado(p, "CANCELADO", self.j, "Solicitud")
        self.assertEqual(
            self.estado(p, "CANCELADO", self.a, "Autoriza dueño")["historial"][-1][
                "usuario_id"
            ],
            self.aid,
        )

    def test_06_bloqueo_edicion(self):
        p = self.estado(self.agregar(self.crear()), "EN_PREPARACION", self.k)
        for f in [
            lambda: self.agregar(p),
            lambda: self.s.editar_detalle(
                self.j, p["id"], p["detalles"][0]["id"], 3, "", p["version"]
            ),
            lambda: self.s.quitar_detalle(
                self.j, p["id"], p["detalles"][0]["id"], p["version"]
            ),
        ]:
            with self.assertRaises(ErrorNegocio):
                f()

    def test_07_permisos_y_propiedad(self):
        p = self.crear()
        self.assertEqual(self.s.listar_pedidos(self.o)["items"], [])
        acciones = [
            lambda: self.s.obtener_pedido(self.o, p["id"]),
            lambda: self.s.crear_pedido(self.k, "LLEVAR"),
            lambda: self.s.guardar_categoria(self.j, "No"),
            lambda: self.s.listar_usuarios(self.k),
            lambda: self.s.cambiar_estado(
                self.j, p["id"], "EN_PREPARACION", p["version"]
            ),
            lambda: self.s.cambiar_estado(
                self.k, p["id"], "CANCELADO", p["version"], "No"
            ),
            lambda: self.s.crear_pedido(self.j, "LLEVAR", responsable_id=self.oid),
        ]
        for f in acciones:
            with self.assertRaises(ErrorNegocio):
                f()

    def test_08_admin_y_reasignacion(self):
        p = self.agregar(self.crear(actor=self.a), self.a)
        self.s.reasignar_pedido(self.a, p["id"], self.jid, None, p["version"], "Turno")
        p = self.s.obtener_pedido(self.j, p["id"])
        p = self.estado(p, "EN_PREPARACION", self.k)
        with self.assertRaises(ErrorNegocio):
            self.estado(p, "LISTO", self.k2)
        self.s.reasignar_pedido(
            self.a, p["id"], None, self.k2id, p["version"], "Relevo"
        )
        p = self.s.obtener_pedido(self.k2, p["id"])
        p = self.estado(p, "LISTO", self.k2)
        self.assertEqual(self.estado(p, "ENTREGADO", self.a)["estado"], "ENTREGADO")

    def test_09_mesa_ocupada(self):
        p = self.crear()
        for f in [
            lambda: self.crear(),
            lambda: self.s.archivar_mesa(self.a, self.mid),
            lambda: self.s.guardar_mesa(self.a, 2, 4, mid=self.mid),
        ]:
            with self.assertRaises(ErrorNegocio):
                f()
        self.estado(p, "CANCELADO", self.a, "Liberar")
        self.s.archivar_mesa(self.a, self.mid)
        with self.assertRaises(ErrorNegocio):
            self.crear()
        self.s.guardar_mesa(self.a, 1, 4, True, self.mid)
        self.assertEqual(self.crear()["estado"], "PENDIENTE")

    def test_10_precio_historico(self):
        p = self.agregar(self.crear())
        self.s.guardar_producto(self.a, "Nuevo", "", "20000", self.cid, pid=self.pid)
        p = self.s.obtener_pedido(self.j, p["id"])
        self.assertEqual(p["total_centavos"], 3700000)
        self.assertEqual(p["detalles"][0]["producto_nombre"], "Hamburguesa")
        self.s.archivar_producto(self.a, self.pid)
        with self.assertRaises(ErrorNegocio):
            self.agregar(p)
        self.assertEqual(self.s.productos(self.j), [])

    def test_11_precios_invalidos(self):
        for precio in [
            "0",
            "-1",
            "NaN",
            "Infinity",
            "1.001",
            "100000000",
            True,
            1.25,
            None,
        ]:
            with self.subTest(precio=precio), self.assertRaises(ErrorNegocio):
                self.s.guardar_producto(self.a, "X", "", precio, self.cid)

    def test_12_cantidades_y_notas(self):
        p = self.crear()
        for n in [0, -1, 100, True, "2", 2.5, None]:
            with self.subTest(n=n), self.assertRaises(ErrorNegocio):
                self.s.agregar_producto(self.j, p["id"], self.pid, n, "", p["version"])
        for notas in [1, "x" * 256, "linea\notra"]:
            with self.subTest(notas=notas), self.assertRaises(ErrorNegocio):
                self.s.agregar_producto(
                    self.j, p["id"], self.pid, 1, notas, p["version"]
                )
        self.assertEqual(self.s.obtener_pedido(self.j, p["id"])["detalles"], [])

    def test_13_idempotencia(self):
        key = str(uuid4())
        a = self.s.crear_pedido(self.j, "LLEVAR", clave=key)
        b = self.s.crear_pedido(self.j, "LLEVAR", clave=key)
        self.assertEqual(a, b)
        with self.assertRaises(ErrorNegocio):
            self.s.crear_pedido(self.j, "SALON", self.mid, clave=key)
        key = str(uuid4())
        p = self.s.obtener_pedido(self.j, a["id"])
        a = self.s.agregar_producto(self.j, p["id"], self.pid, 1, "", p["version"], key)
        b = self.s.agregar_producto(self.j, p["id"], self.pid, 1, "", p["version"], key)
        self.assertEqual(a, b)
        self.assertEqual(len(self.s.obtener_pedido(self.j, p["id"])["detalles"]), 1)
        self.assertEqual(self.s.consultar_operacion(self.j, key)["resultado"], a)
        with self.assertRaises(ErrorNegocio):
            self.s.consultar_operacion(self.o, key)

    def test_14_version_obsoleta(self):
        p = self.crear()
        self.agregar(p)
        with self.assertRaises(ErrorNegocio):
            self.agregar(p)

    def test_15_usuario_con_pedidos(self):
        p = self.crear()
        for f in [
            lambda: self.s.desactivar_usuario(self.a, self.jid),
            lambda: self.s.desactivar_usuario(self.a, self.aid),
            lambda: self.s.guardar_usuario(
                self.a, "Juan", "juan", "COCINA", uid=self.jid
            ),
        ]:
            with self.assertRaises(ErrorNegocio):
                f()
        self.s.reasignar_pedido(self.a, p["id"], self.oid, None, p["version"], "Turno")
        self.s.desactivar_usuario(self.a, self.jid)
        with self.assertRaises(ErrorNegocio):
            self.s.perfil(self.j)
        self.s.guardar_usuario(self.a, "Juan", "juan", "MESERO", True, uid=self.jid)
        self.assertTrue(self.s.iniciar_sesion("juan", PROPIA))

    def test_16_clave_temporal_y_revocacion(self):
        self.s.guardar_usuario(
            self.a, "Juan", "juan", "MESERO", password=TEMP, uid=self.jid
        )
        with self.assertRaises(ErrorNegocio):
            self.s.perfil(self.j)
        token = self.s.iniciar_sesion("juan", TEMP)
        self.assertTrue(self.s.perfil(token)["debe_cambiar"])
        with self.assertRaises(ErrorNegocio):
            self.s.productos(token)
        self.s.cambiar_clave(token, TEMP, PROPIA)
        with self.assertRaises(ErrorNegocio):
            self.s.perfil(token)

    def test_17_bloqueo_login(self):
        for _ in range(5):
            with self.assertRaises(ErrorNegocio):
                self.s.iniciar_sesion("juan", "incorrecta")
        with self.assertRaisesRegex(ErrorNegocio, "bloqueada"):
            self.s.iniciar_sesion("juan", PROPIA)
        self.s.guardar_usuario(
            self.a, "Juan", "juan", "MESERO", password=TEMP, uid=self.jid
        )
        self.assertTrue(self.s.iniciar_sesion("juan", TEMP))

    def test_18_inmutabilidad(self):
        self.crear()
        for t in ["historial", "auditoria"]:
            for sentencia in [
                f"UPDATE {t} SET usuario_id=usuario_id",
                f"DELETE FROM {t}",
            ]:
                with self.subTest(sql=sentencia), self.assertRaises(ErrorBase):
                    with self.b.transaccion(True) as c:
                        c.execute(sentencia)

    def test_19_crud_y_duplicados(self):
        cid = self.s.guardar_categoria(self.a, "Bebidas")["id"]
        self.s.guardar_categoria(self.a, "Jugos", cid)
        with self.assertRaises(ErrorBase):
            self.s.guardar_categoria(self.a, "Jugos")
        self.s.eliminar_categoria(self.a, cid)
        with self.assertRaises(ErrorBase):
            self.s.guardar_mesa(self.a, 1, 4)
        with self.assertRaises(ErrorBase):
            self.s.guardar_usuario(self.a, "Otro", "JUAN", "MESERO", password=TEMP)

    def test_20_persistencia_y_respaldo(self):
        p = self.agregar(self.crear())
        self.b.inicializar()
        s = Restaurante(Base(ruta=self.b.ruta))
        self.assertEqual(s.obtener_pedido(self.j, p["id"])["total_centavos"], 3700000)
        destino = Path(self.tmp.name) / "copia.db"
        self.s.respaldar(self.a, destino)
        self.assertEqual(
            Restaurante(Base(ruta=destino)).obtener_pedido(self.j, p["id"])[
                "total_centavos"
            ],
            3700000,
        )
        with self.assertRaises(ErrorBase):
            self.s.respaldar(self.a, destino)
        with self.assertRaises(ErrorNegocio):
            self.s.respaldar(self.j, Path(self.tmp.name) / "no.db")

    def test_21_reportes_sin_datos_y_fechas(self):
        for d, h in [
            ("x", "y"),
            ("2026-03-01", "2026-02-01"),
            ("2020-01-01", "2026-01-01"),
        ]:
            with self.subTest(d=d), self.assertRaises(ErrorNegocio):
                self.s.ventas(self.a, d, h)
        hoy = datetime.now(timezone.utc).date().isoformat()
        self.assertEqual(self.s.ventas(self.a, hoy, hoy)["total_centavos"], 0)
        self.assertIsNone(self.s.tiempos(self.a, hoy, hoy)["promedio_segundos"])
        with self.assertRaises(ErrorNegocio):
            self.s.ventas(self.j, hoy, hoy)

    def test_22_inspeccion_segura(self):
        self.assertNotIn(
            "password_hash", self.s.inspeccionar(self.a, "usuario")["items"][0]
        )
        for t in ["sesion", "operacion", "usuario; DROP TABLE usuario"]:
            with self.subTest(t=t), self.assertRaises(ErrorNegocio):
                self.s.inspeccionar(self.a, t)
        with self.assertRaises(ErrorNegocio):
            self.s.inspeccionar(self.j, "usuario")

    def test_23_hash_y_token(self):
        h = hash_clave(ADMIN)
        self.assertNotIn(ADMIN, h)
        self.assertTrue(verificar_clave(ADMIN, h))
        self.assertFalse(verificar_clave("otra", h))
        with self.b.transaccion() as c:
            c.execute("SELECT token_hash FROM sesion")
            self.assertNotIn(self.a, [r["token_hash"] for r in c.all()])
        with self.assertRaises(ErrorNegocio):
            self.s.productos(str(self.aid))

    def test_24_archivo_reactivacion(self):
        self.s.archivar_producto(self.a, self.pid)
        self.assertEqual(self.s.productos(self.j), [])
        self.s.guardar_producto(
            self.a, "Hamburguesa", "", "18500", self.cid, True, True, self.pid
        )
        self.assertEqual(len(self.s.productos(self.j)), 1)

    def test_25_lineas_repetidas(self):
        p = self.agregar(self.agregar(self.crear()), cantidad=1)
        self.assertEqual(len(p["detalles"]), 2)
        self.assertEqual(p["total_centavos"], 5550000)

    def test_26_servicio_salon_llevar(self):
        for tipo, mesa in [
            ("SALON", None),
            ("LLEVAR", self.mid),
            ("DOMICILIO", None),
            ("SALON", True),
        ]:
            with self.subTest(tipo=tipo), self.assertRaises(ErrorNegocio):
                self.s.crear_pedido(self.j, tipo, mesa)
        self.assertIsNone(self.crear(False)["mesa_id"])

    def test_27_rollback_atomico(self):
        p = self.agregar(self.crear())
        with patch.object(
            self.s, "_historial", side_effect=RuntimeError("Fallo simulado")
        ):
            with self.assertRaises(RuntimeError):
                self.estado(p, "CANCELADO", self.a, "Prueba")
        r = self.s.obtener_pedido(self.j, p["id"])
        self.assertEqual((r["estado"], r["version"]), ("PENDIENTE", p["version"]))
        self.assertEqual(self.s.mesas(self.j)[0]["estado"], "OCUPADA")

    def test_28_veinte_creaciones_concurrentes(self):
        with ThreadPoolExecutor(max_workers=20) as pool:
            ids = list(
                pool.map(
                    lambda _: self.s.crear_pedido(self.j, "LLEVAR", clave=str(uuid4()))[
                        "id"
                    ],
                    range(20),
                )
            )
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(len(self.s.listar_pedidos(self.j)["items"]), 20)

    def test_29_reserva_concurrente(self):
        def crear(token):
            try:
                return self.s.crear_pedido(token, "SALON", self.mid)["id"]
            except ErrorNegocio:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            r = list(pool.map(crear, [self.j, self.o]))
        self.assertEqual(sum(x is not None for x in r), 1)

    def test_30_idempotencia_concurrente(self):
        key = str(uuid4())
        with ThreadPoolExecutor(max_workers=2) as pool:
            r = list(
                pool.map(
                    lambda _: self.s.crear_pedido(self.j, "LLEVAR", clave=key), range(2)
                )
            )
        self.assertEqual(r[0], r[1])
        self.assertEqual(len(self.s.listar_pedidos(self.j)["items"]), 1)

    def test_31_cocina_concurrente(self):
        p = self.agregar(self.crear())

        def tomar(token):
            try:
                return self.s.cambiar_estado(
                    token, p["id"], "EN_PREPARACION", p["version"]
                )
            except ErrorNegocio:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            r = list(pool.map(tomar, [self.k, self.k2]))
        self.assertEqual(sum(x is not None for x in r), 1)
        self.assertEqual(len(self.s.obtener_pedido(self.a, p["id"])["historial"]), 2)

    def test_32_limites_entradas(self):
        for nombre in ["", "x" * 101, "Nombre\x1b[31m"]:
            with self.subTest(nombre=nombre), self.assertRaises(ErrorNegocio):
                self.s.guardar_producto(self.a, nombre, "", "1", self.cid)
        for numero in [0, True, -1, 10000]:
            with self.subTest(numero=numero), self.assertRaises(ErrorNegocio):
                self.s.guardar_mesa(self.a, numero)

    def test_33_cancelacion_necesita_motivo(self):
        p = self.crear()
        with self.assertRaises(ErrorNegocio):
            self.estado(p, "CANCELADO", self.j)
        self.assertEqual(self.s.obtener_pedido(self.j, p["id"])["estado"], "PENDIENTE")

    def test_34_base_ajena_intacta(self):
        ruta = Path(self.tmp.name) / "ajena.db"
        with sqlite3.connect(ruta) as c:
            c.execute("CREATE TABLE ajena(id INTEGER)")
        with self.assertRaises(ErrorBase):
            Base(ruta=ruta).inicializar()
        with sqlite3.connect(ruta) as c:
            self.assertEqual(
                c.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall(),
                [("ajena",)],
            )

    def test_36_categoria_historica(self):
        self.agregar(self.crear())
        otra = self.s.guardar_categoria(self.a, "Otra")["id"]
        self.s.guardar_producto(self.a, "Hamburguesa", "", "18500", otra, pid=self.pid)
        with self.assertRaises(ErrorNegocio):
            self.s.eliminar_categoria(self.a, self.cid)

    def test_37_cierre_sesion(self):
        self.s.cerrar_sesion(self.j)
        with self.assertRaises(ErrorNegocio):
            self.s.productos(self.j)

    def test_38_paginacion(self):
        with self.assertRaises(ErrorNegocio):
            self.s.listar_pedidos(self.j, pagina=0)
        self.assertEqual(self.s.listar_pedidos(self.j, pagina=2)["items"], [])

    def test_39_relevo_cocina_y_desactivacion(self):
        p = self.estado(self.agregar(self.crear()), "EN_PREPARACION", self.k)
        with self.assertRaises(ErrorNegocio):
            self.s.desactivar_usuario(self.a, self.kid)
        self.s.reasignar_pedido(
            self.a, p["id"], None, self.k2id, p["version"], "Relevo"
        )
        self.s.desactivar_usuario(self.a, self.kid)
        with self.assertRaises(ErrorNegocio):
            self.s.perfil(self.k)


if __name__ == "__main__":
    unittest.main()
