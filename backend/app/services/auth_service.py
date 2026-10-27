"""Inicio de sesión, bloqueo por intentos y recuperación de contraseña."""
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    HASH_RELLENO, crear_token, hash_token, hashear_password, nuevo_token_recuperacion, verificar_password,
)
from app.db.base import ahora
from app.models import IntentoLogin, RecuperacionPassword, Usuario
from app.services import usuario_service
from app.services.errores import ErrorNegocio

# PG-01: mismo mensaje si falla el correo o la contraseña (no revela cuál).
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."
MENSAJE_ENLACE_INVALIDO = "El enlace no es válido o ya venció. Pide uno nuevo."


def _clave(email: str) -> str:
    return usuario_service.normalizar_email(email)[:120]


def autenticar(db: Session, email: str, password: str) -> Usuario:
    cfg = get_settings()
    clave = _clave(email)
    intento = db.get(IntentoLogin, clave)
    momento = ahora()

    # Si está bloqueado, se rechaza SIN mirar la contraseña (ni siquiera la correcta).
    if intento and intento.bloqueado_hasta and intento.bloqueado_hasta > momento:
        faltan = max(1, int((intento.bloqueado_hasta - momento).total_seconds() // 60) + 1)
        raise ErrorNegocio(
            f"Demasiados intentos fallidos. Intenta de nuevo en {faltan} minutos o recupera tu contraseña.",
            429, "login_bloqueado",
        )

    usuario = usuario_service.buscar_por_email(db, email)
    # Siempre se compara una contraseña (aunque el correo no exista): misma demora, misma respuesta.
    password_ok = verificar_password(password, usuario.password_hash if usuario else HASH_RELLENO)

    if usuario is None or not password_ok:
        if intento is None:
            intento = IntentoLogin(email=clave, fallidos=0)
            db.add(intento)
        intento.fallidos += 1
        if intento.fallidos >= cfg.login_max_intentos:
            intento.fallidos = 0
            intento.bloqueado_hasta = momento + timedelta(minutes=cfg.login_bloqueo_minutos)
            db.commit()
            raise ErrorNegocio(
                f"Demasiados intentos fallidos. Tu acceso se bloqueó por {cfg.login_bloqueo_minutos} minutos.",
                429, "login_bloqueado",
            )
        db.commit()
        raise ErrorNegocio(MENSAJE_CREDENCIALES, 401)

    if intento is not None:  # entró bien: el contador vuelve a cero
        db.delete(intento)
        db.commit()
    return usuario


def emitir_token(usuario: Usuario) -> str:
    return crear_token(usuario.id, usuario.token_version)


def solicitar_recuperacion(db: Session, email: str) -> tuple[Usuario, str] | None:
    """Crea el enlace de recuperación si el correo existe. Devuelve (usuario, token) o None.
    La API responde LO MISMO en ambos casos, para no revelar qué correos están registrados."""
    usuario = usuario_service.buscar_por_email(db, email)
    if usuario is None:
        return None
    # Un enlace nuevo anula los anteriores.
    db.execute(
        update(RecuperacionPassword)
        .where(RecuperacionPassword.usuario_id == usuario.id, RecuperacionPassword.usado_at.is_(None))
        .values(usado_at=ahora())
    )
    token, token_hash = nuevo_token_recuperacion()
    db.add(RecuperacionPassword(
        usuario_id=usuario.id, token_hash=token_hash,
        expira_at=ahora() + timedelta(minutes=get_settings().recuperacion_minutos),
    ))
    db.commit()
    return usuario, token


def restablecer_password(db: Session, token: str, nueva_password: str) -> None:
    rec = db.scalar(select(RecuperacionPassword).where(RecuperacionPassword.token_hash == hash_token(token)))
    momento = ahora()
    if rec is None or rec.usado_at is not None or rec.expira_at < momento:
        raise ErrorNegocio(MENSAJE_ENLACE_INVALIDO, 400, "enlace_invalido")

    usuario = db.get(Usuario, rec.usuario_id)
    usuario.password_hash = hashear_password(nueva_password)
    usuario.token_version += 1  # cierra todas las sesiones abiertas en otros celulares
    rec.usado_at = momento  # se usa una sola vez
    intento = db.get(IntentoLogin, _clave(usuario.email))
    if intento is not None:  # si estaba bloqueado, recuperar la contraseña lo libera
        db.delete(intento)
    db.commit()
