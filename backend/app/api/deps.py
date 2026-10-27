"""Dependencias reutilizables: quién es el usuario actual."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import leer_token
from app.db.session import get_db
from app.models import Usuario

_bearer = HTTPBearer(auto_error=False)


def _no_autenticado(detalle: str = "Tu sesión venció. Inicia sesión nuevamente.") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detalle, headers={"WWW-Authenticate": "Bearer"})


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise _no_autenticado("Debes iniciar sesión.")
    datos = leer_token(credenciales.credentials)
    if datos is None:
        raise _no_autenticado()

    try:
        usuario = db.get(Usuario, int(datos["sub"]))
        version = int(datos["tv"])
    except (KeyError, ValueError, TypeError):
        raise _no_autenticado()

    # Se revisa en la base de datos en CADA petición: si la cuenta se borró o se cambió la contraseña,
    # los tokens anteriores dejan de servir al instante (no hay que esperar a que venzan).
    if usuario is None or usuario.token_version != version:
        raise _no_autenticado()
    return usuario
