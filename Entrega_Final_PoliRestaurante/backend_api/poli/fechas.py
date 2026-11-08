"""Fecha comercial del restaurante y conversión a las marcas UTC persistidas."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .errores import ErrorNegocio, exigir

ZONA_COLOMBIA = "America/Bogota"
BOGOTA = ZoneInfo(ZONA_COLOMBIA)


def marca_utc(instante):
    return instante.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def rango_utc_colombia(desde, hasta):
    """Incluye el inicio local y excluye la medianoche local posterior a 'hasta'."""
    try:
        primer_dia, ultimo_dia = date.fromisoformat(desde), date.fromisoformat(hasta)
        if (primer_dia.isoformat(), ultimo_dia.isoformat()) != (desde, hasta):
            raise ValueError
        exigir(
            0 <= (ultimo_dia - primer_dia).days < 366,
            "Periodo inválido: máximo 366 días e inicio anterior o igual al final.",
        )
        inicio = datetime.combine(primer_dia, time.min, BOGOTA)
        fin = datetime.combine(ultimo_dia + timedelta(days=1), time.min, BOGOTA)
        return marca_utc(inicio), marca_utc(fin)
    except (ValueError, TypeError, OverflowError):
        raise ErrorNegocio(
            "DATO_INVALIDO", "Fechas válidas con formato AAAA-MM-DD."
        ) from None


def leer_instante_utc(valor):
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))
