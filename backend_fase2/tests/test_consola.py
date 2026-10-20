"""Recorre el menú verdadero con entrada simulada, sin sembrar datos de negocio."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import unittest
import sqlite3
import main


class ConsolaTests(unittest.TestCase):
    def test_menu_completo_tres_roles(self):
        entradas = []
        claves = []
        admin = "AdminSegura123!"
        temporal = "TemporalSegura123!"
        personal = "PersonalSegura123!"

        def agregar(*datos):
            entradas.extend(datos)

        def login(usuario, clave):
            agregar("1", usuario)
            claves.append(clave)

        def crear_usuario(nombre, usuario, rol):
            agregar("30", "1", nombre, usuario, rol, "", "")
            claves.extend([temporal, temporal])

        agregar("Dueño", "admin")
        claves.extend([admin, admin])
        login("admin", admin)
        crear_usuario("Juan Parra", "juan", "MESERO")
        crear_usuario("Cocina", "cocina", "COCINA")
        agregar("31", "1", "Comidas", "")
        agregar("32", "1", "Hamburguesa", "De la casa", "18500", "1", "", "", "")
        agregar("33", "1", "1", "4", "", "")
        agregar("43", "usuario", "0")
        login("juan", temporal)
        claves.extend([temporal, personal, personal])
        login("juan", personal)
        agregar("10", "", "1", "")
        agregar("11", "1", "1", "2", "Sin cebolla", "")
        agregar("11", "1", "1", "1", "Con salsa", "")
        agregar("12", "1", "1", "3", "Sin sal", "")
        agregar("13", "1", "2", "s")
        agregar("4", "1", "0")
        login("cocina", temporal)
        claves.extend([temporal, personal, personal])
        login("cocina", personal)
        agregar("3", "", "", "20", "1", "s", "21", "1", "s", "0")
        login("juan", personal)
        agregar("14", "1", "s", "10", "s", "", "15", "2", "Cliente se retira", "s", "0")
        login("admin", admin)
        hoy = datetime.now(timezone.utc).date().isoformat()
        agregar(
            "40",
            hoy,
            hoy,
            "",
            "",
            "n",
            "41",
            hoy,
            hoy,
            "n",
            "42",
            "n",
            "43",
            "pedido",
            "44",
            "s",
            "0",
            "0",
        )
        e = iter(entradas)
        p = iter(claves)
        salida = StringIO()
        with TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "datos.db"
            with patch("builtins.input", side_effect=lambda _: next(e)), patch(
                "getpass.getpass", side_effect=lambda _: next(p)
            ), patch("poli.menu.RAIZ", Path(tmp)), redirect_stdout(salida):
                resultado = main.main(["--base", str(ruta)])
            self.assertEqual(resultado, 0)
            self.assertNotIn("[AVISO]", salida.getvalue())
            self.assertNotIn("[BASE]", salida.getvalue())
            for secreto in claves:
                self.assertNotIn(secreto, salida.getvalue())
            with sqlite3.connect(ruta) as c:
                self.assertEqual(
                    c.execute("SELECT estado FROM pedido ORDER BY id").fetchall(),
                    [("ENTREGADO",), ("CANCELADO",)],
                )
                self.assertEqual(
                    c.execute(
                        "SELECT SUM(precio_centavos*cantidad) FROM detalle WHERE pedido_id=1"
                    ).fetchone()[0],
                    5550000,
                )
                self.assertEqual(c.execute("SELECT COUNT(*) FROM ocupacion").fetchone()[0], 0)
                self.assertEqual(c.execute("SELECT COUNT(*) FROM usuario").fetchone()[0], 3)
            self.assertEqual(len(list((Path(tmp) / "respaldos").glob("*.db"))), 1)
            self.assertIsNone(next(e, None))
            self.assertIsNone(next(p, None))


if __name__ == "__main__":
    unittest.main()
