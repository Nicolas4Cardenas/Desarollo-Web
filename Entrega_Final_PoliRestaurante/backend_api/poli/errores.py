class ErrorNegocio(Exception):
    """Error esperado que puede corregir el cliente de la API."""

    def __init__(self, codigo, mensaje):
        self.codigo = codigo
        super().__init__(mensaje)


class ErrorBase(Exception):
    """Fallo de conexión, instalación o restricción de la base."""

    def __init__(self, mensaje, codigo="BASE"):
        self.codigo = codigo
        super().__init__(mensaje)


def exigir(condicion, mensaje, codigo="DATO_INVALIDO"):
    if not condicion:
        raise ErrorNegocio(codigo, mensaje)
