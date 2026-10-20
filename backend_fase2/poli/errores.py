class ErrorNegocio(Exception):
    """Error esperado que puede corregir la persona que usa el menú."""

    def __init__(self, codigo, mensaje):
        self.codigo = codigo
        super().__init__(mensaje)


class ErrorBase(Exception):
    """Fallo de conexión, instalación o restricción de la base."""


def exigir(condicion, mensaje, codigo="DATO_INVALIDO"):
    if not condicion:
        raise ErrorNegocio(codigo, mensaje)
