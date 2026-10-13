"""Utilidades de consola: colores, tablas, menús y lectura validada de datos."""
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Callable, List, Optional, Sequence, Tuple

from .errores import mensaje_error

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
if _COLOR and os.name == "nt":
    os.system("")  # activa secuencias ANSI en Windows 10+


class Cancelado(Exception):
    """El usuario dejó una respuesta vacía para cancelar la operación."""


# ------------------------------------------------------------------ colores
def _c(texto, codigo: str) -> str:
    return f"\033[{codigo}m{texto}\033[0m" if _COLOR else str(texto)


def negrita(t): return _c(t, "1")
def tenue(t): return _c(t, "2")
def rojo(t): return _c(t, "31")
def verde(t): return _c(t, "32")
def amarillo(t): return _c(t, "33")
def cian(t): return _c(t, "36")


def ok(msg): print(verde("✔ ") + str(msg))
def error(msg): print(rojo("✘ ") + str(msg))
def aviso(msg): print(amarillo("! ") + str(msg))
def info(msg): print(cian("• ") + str(msg))


# ----------------------------------------------------------------- formatos
def dinero(valor) -> str:
    if valor is None:
        return "-"
    return "$" + f"{Decimal(valor):,.0f}".replace(",", ".")


def num(valor, decimales: int = 0) -> str:
    if valor is None:
        return "-"
    return f"{Decimal(valor):.{decimales}f}"


def fecha_hora(valor) -> str:
    return valor.strftime("%Y-%m-%d %H:%M") if valor else "-"


def si_no(valor) -> str:
    return "Sí" if valor else "No"


def recortar(texto, n: int = 40) -> str:
    texto = "" if texto is None else str(texto)
    return texto if len(texto) <= n else texto[: n - 1] + "…"


# ------------------------------------------------------------------- tablas
def tabla(columnas: Sequence[str], filas: Sequence[Sequence], derecha: Sequence[int] = ()) -> None:
    filas = [["" if v is None else str(v) for v in f] for f in filas]
    anchos = [max([len(c)] + [len(f[i]) for f in filas]) for i, c in enumerate(columnas)]
    linea = "+" + "+".join("-" * (a + 2) for a in anchos) + "+"

    def fila(vals, cabecera=False):
        celdas = []
        for i, v in enumerate(vals):
            celdas.append(v.rjust(anchos[i]) if (i in derecha and not cabecera) else v.ljust(anchos[i]))
        return "| " + " | ".join(celdas) + " |"

    print(linea)
    print(negrita(fila(columnas, cabecera=True)))
    print(linea)
    for f in filas:
        print(fila(f))
    print(linea)


def banner(titulo: str) -> None:
    ancho = max(44, len(titulo) + 6)
    print(cian("=" * ancho))
    print(negrita(titulo.center(ancho)))
    print(cian("=" * ancho))


def limpiar() -> None:
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def pausar() -> None:
    try:
        input(tenue("\nPresiona Enter para continuar..."))
    except (EOFError, KeyboardInterrupt):
        print()


# ------------------------------------------------------------------ lectura
def parsear_decimal(texto: str) -> Decimal:
    """Acepta 12000, 12.000 (miles estilo CO), 12000,50 o 12000.50."""
    t = texto.strip().replace("$", "").replace(" ", "")
    if not t:
        raise ValueError("vacío")
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d+)?$", t):
        t = t.replace(".", "").replace(",", ".")
    elif "," in t and "." not in t:
        t = t.replace(",", ".")
    try:
        d = Decimal(t)
    except InvalidOperation:
        raise ValueError("no es un número")
    if not d.is_finite():
        raise ValueError("no es un número")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parsear_fecha(texto: str) -> date:
    t = texto.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(t, formato).date()
        except ValueError:
            pass
    raise ValueError("formato de fecha inválido")


def _pedir(msg: str, defecto=None) -> str:
    sufijo = f" [{defecto}]" if defecto not in (None, "") else ""
    return input(f"{msg}{sufijo}: ").strip()


def leer_texto(msg: str, defecto: Optional[str] = None, maximo: Optional[int] = None) -> str:
    while True:
        v = _pedir(msg, defecto)
        if v == "":
            if defecto not in (None, ""):
                return defecto
            raise Cancelado()
        if maximo and len(v) > maximo:
            error(f"Máximo {maximo} caracteres.")
            continue
        return v


def leer_texto_opcional(msg: str, defecto: Optional[str] = None, maximo: Optional[int] = None) -> Optional[str]:
    """Enter = conservar el valor actual (o nada); '-' = dejarlo vacío."""
    while True:
        v = _pedir(msg + (" ('-' para borrar)" if defecto else ""), defecto)
        if v == "":
            return defecto or None
        if v == "-":
            return None
        if maximo and len(v) > maximo:
            error(f"Máximo {maximo} caracteres.")
            continue
        return v


def leer_entero(msg: str, minimo: Optional[int] = None, maximo: Optional[int] = None,
                defecto: Optional[int] = None, opcional: bool = False) -> Optional[int]:
    while True:
        v = _pedir(msg, defecto)
        if v == "":
            if defecto is not None:
                return defecto
            if opcional:
                return None
            raise Cancelado()
        try:
            n = int(v)
        except ValueError:
            error("Escribe un número entero.")
            continue
        if minimo is not None and n < minimo:
            error(f"El valor mínimo es {minimo}.")
            continue
        if maximo is not None and n > maximo:
            error(f"El valor máximo es {maximo}.")
            continue
        return n


def leer_decimal(msg: str, minimo: Decimal = Decimal("0"), defecto: Optional[Decimal] = None) -> Decimal:
    while True:
        v = _pedir(msg, None if defecto is None else f"{defecto:.0f}")
        if v == "":
            if defecto is not None:
                return defecto
            raise Cancelado()
        try:
            d = parsear_decimal(v)
        except ValueError as e:
            error(f"Valor inválido ({e}). Ejemplo: 12000")
            continue
        if d < minimo:
            error(f"El valor mínimo es {minimo}.")
            continue
        if d > Decimal("99999999.99"):
            error("El valor es demasiado grande.")
            continue
        return d


def leer_fecha(msg: str, defecto: date) -> date:
    while True:
        v = _pedir(msg, defecto.isoformat())
        if v == "":
            return defecto
        try:
            return parsear_fecha(v)
        except ValueError:
            error("Usa el formato AAAA-MM-DD (ej: 2026-10-13).")


def confirmar(msg: str, defecto: bool = False) -> bool:
    sufijo = "S/n" if defecto else "s/N"
    v = input(f"{msg} ({sufijo}): ").strip().lower()
    if v == "":
        return defecto
    return v in ("s", "si", "sí", "y", "yes")


def elegir(msg: str, opciones: Sequence[str], opcional: bool = False) -> Optional[str]:
    for i, o in enumerate(opciones, 1):
        print(f"  {i}. {o}")
    n = leer_entero(msg, minimo=1, maximo=len(opciones), opcional=opcional)
    return None if n is None else opciones[n - 1]


# ------------------------------------------------------------ ejecución/menú
def ejecutar(accion: Callable[[], None]) -> bool:
    """Corre una acción mostrando los errores de forma amigable. True si terminó bien."""
    try:
        accion()
        return True
    except Cancelado:
        info("Operación cancelada.")
    except KeyboardInterrupt:
        print()
        info("Operación cancelada.")
    except Exception as exc:  # noqa: BLE001
        msg = mensaje_error(exc)
        error(msg if msg else f"Error inesperado ({type(exc).__name__}): {exc}")
    return False


def menu(titulo: str, opciones: List[Tuple[str, Callable[[], None]]], salida: str = "Volver",
         subtitulo: Optional[str] = None) -> None:
    while True:
        limpiar()
        banner(titulo)
        if subtitulo:
            print(tenue(subtitulo))
        print()
        for i, (etiqueta, _) in enumerate(opciones, 1):
            print(f"  {i}. {etiqueta}")
        print(f"  0. {salida}")
        try:
            op = input("\nElige una opción: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if op == "0":
            return
        if not op.isdigit() or not 1 <= int(op) <= len(opciones):
            aviso("Opción no válida.")
            pausar()
            continue
        print(tenue("(En cualquier pregunta, Enter vacío cancela)\n"))
        ejecutar(opciones[int(op) - 1][1])
        pausar()
