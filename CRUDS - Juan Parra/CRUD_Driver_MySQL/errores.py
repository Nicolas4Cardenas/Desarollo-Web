"""Errores de negocio comunes a toda la aplicación."""


class ErrorNegocio(Exception):
    """Regla de negocio incumplida (mesa ocupada, pedido bloqueado, sin permiso, etc.)."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje

    def __str__(self):
        return f"[{self.codigo}] {self.mensaje}"


class _SinCambio:
    """Marca para indicar 'no modificar este campo' (distinto de None, que borra)."""

    def __repr__(self):
        return "SIN_CAMBIO"


SIN_CAMBIO = _SinCambio()
