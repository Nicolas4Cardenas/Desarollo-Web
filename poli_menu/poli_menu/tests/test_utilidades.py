"""Pruebas que no necesitan base de datos:  pytest"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from poli.sqlscript import dividir_sentencias  # noqa: E402
from poli.ui import parsear_decimal, parsear_fecha  # noqa: E402


def test_script_sql_se_divide_bien():
    texto = (RAIZ / "backend.sql").read_text(encoding="utf-8")
    sents = list(dividir_sentencias(texto))
    assert sents[0].startswith("DROP DATABASE")
    assert sum(s.startswith("CREATE PROCEDURE") for s in sents) == texto.count("CREATE PROCEDURE")
    assert sum(s.startswith("CREATE TRIGGER") for s in sents) == texto.count("CREATE TRIGGER")
    assert sum(s.startswith("CREATE TABLE") for s in sents) == texto.count("CREATE TABLE")
    assert not any("DELIMITER" in s.upper().split()[:1] for s in sents)
    # ninguna sentencia debe terminar con el delimitador
    assert not any(s.endswith("$$") for s in sents)


def test_delimiter_simple():
    sql = "DELIMITER $$\nCREATE PROCEDURE p()\nBEGIN\n  SELECT 1;\nEND$$\nDELIMITER ;\nSELECT 2;\n"
    assert list(dividir_sentencias(sql)) == ["CREATE PROCEDURE p()\nBEGIN\n  SELECT 1;\nEND", "SELECT 2"]


@pytest.mark.parametrize("texto,esperado", [
    ("12000", "12000.00"), ("12.000", "12000.00"), ("$ 1.250.000", "1250000.00"),
    ("12000,50", "12000.50"), ("12000.5", "12000.50"), ("0", "0.00"),
])
def test_parsear_decimal(texto, esperado):
    assert parsear_decimal(texto) == Decimal(esperado)


@pytest.mark.parametrize("texto", ["", "abc", "1,500.50", "NaN"])
def test_parsear_decimal_invalido(texto):
    with pytest.raises(ValueError):
        parsear_decimal(texto)


def test_parsear_fecha():
    assert parsear_fecha("2026-10-13") == date(2026, 10, 13)
    assert parsear_fecha("13/10/2026") == date(2026, 10, 13)
    with pytest.raises(ValueError):
        parsear_fecha("13-13-2026")
