class ErrorNegocio(Exception):
    """Error esperado (ej. 'correo ya registrado'). La API lo convierte en una respuesta clara.

    `codigo` es una etiqueta corta para que la app sepa qué hacer (ej. mostrar la pantalla de consentimiento).
    """

    def __init__(self, mensaje: str, status: int = 400, codigo: str | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status = status
        self.codigo = codigo
