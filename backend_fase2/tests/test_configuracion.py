import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from poli.db import Base
from poli.errores import ErrorBase


class ConfiguracionTests(unittest.TestCase):
    def test_configuracion_mysql_validada_sin_conectar(self):
        valido = {
            "host": "127.0.0.1",
            "port": 3306,
            "user": "prueba",
            "database": "prueba",
            "password": "Privada",
        }
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "config.json"
            with patch.dict("os.environ", {}, clear=True):
                for campo, valor in [
                    ("host", []),
                    ("port", True),
                    ("port", 0),
                    ("port", "3306"),
                    ("password", 5),
                    ("database", ""),
                ]:
                    d = dict(valido)
                    d[campo] = valor
                    p.write_text(json.dumps(d))
                    with self.subTest(campo=campo, valor=valor), self.assertRaises(ErrorBase):
                        Base.mysql_desde_archivo(p)
                p.write_text(json.dumps(valido))
                self.assertEqual(Base.mysql_desde_archivo(p).motor, "mysql")
            with patch.dict("os.environ", {"POLI_DB_PASSWORD": "OtraClave"}, clear=True):
                self.assertEqual(Base.mysql_desde_archivo(p).configuracion["password"], "OtraClave")


if __name__ == "__main__":
    unittest.main()
