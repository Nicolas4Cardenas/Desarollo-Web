import hashlib
import hmac
import secrets
from .validaciones import clave

ITERACIONES = 310000


def hash_clave(password):
    clave(password)
    sal = secrets.token_hex(16)
    derivada = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(sal), ITERACIONES
    )
    return f"pbkdf2_sha256${ITERACIONES}${sal}${derivada.hex()}"


def verificar_clave(password, guardada):
    try:
        algoritmo, iteraciones, sal, derivada = guardada.split("$")
        if algoritmo != "pbkdf2_sha256" or not 10000 <= int(iteraciones) <= 1000000:
            return False
        prueba = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(sal), int(iteraciones)
        )
        return hmac.compare_digest(prueba.hex(), derivada)
    except (ValueError, AttributeError, UnicodeError):
        return False


def huella_token(token):
    return hashlib.sha256(str(token).encode()).hexdigest()
