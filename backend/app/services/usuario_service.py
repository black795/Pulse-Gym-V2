"""Cuenta del usuario: crear, buscar, borrar."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hashear_password
from app.models import FotoMaquina, IntentoLogin, Usuario
from app.schemas.auth import UsuarioOut
from app.services import fotos_storage
from app.services.errores import ErrorNegocio

# Sin estos cuatro datos la IA no puede armar el plan (PG-02).
CAMPOS_PARA_PLAN = ("objetivo", "nivel", "dias_por_semana", "minutos_por_sesion")


def campos_faltantes(u: Usuario) -> list[str]:
    obj = u.objetivo
    return [c for c in CAMPOS_PARA_PLAN if obj is None or getattr(obj, c) is None]


def a_usuario_out(u: Usuario) -> UsuarioOut:
    return UsuarioOut(
        id=u.id, nombre=u.nombre, email=u.email,
        consentimiento_estado=u.consentimiento_estado,  # type: ignore[arg-type]
        perfil_completo=not campos_faltantes(u),
        created_at=u.created_at,
    )


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def buscar_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == normalizar_email(email)))


def crear_usuario(db: Session, *, nombre: str, email: str, password: str) -> Usuario:
    email = normalizar_email(email)
    if buscar_por_email(db, email) is not None:
        # PG-01: mensaje claro (la app ofrece iniciar sesión).
        raise ErrorNegocio("Ese correo ya está registrado. Inicia sesión.", 409, "correo_existente")
    usuario = Usuario(nombre=nombre, email=email, password_hash=hashear_password(password))
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:  # dos registros simultáneos con el mismo correo
        db.rollback()
        raise ErrorNegocio("Ese correo ya está registrado. Inicia sesión.", 409, "correo_existente")
    db.refresh(usuario)
    return usuario


def eliminar_cuenta(db: Session, usuario: Usuario) -> tuple[str, str]:
    """Borra la cuenta y TODOS sus datos de inmediato (perfil, mediciones, lesiones…).
    Devuelve (correo, nombre) para poder enviar la confirmación. PG-05 pide hacerlo en máximo 30 días."""
    email, nombre = usuario.email, usuario.nombre
    # PG-48: también se borran los archivos de sus fotos (las filas caen en cascada con la cuenta).
    archivos = [a for a in db.scalars(select(FotoMaquina.archivo).where(FotoMaquina.usuario_id == usuario.id)) if a]
    intento = db.get(IntentoLogin, email[:120])
    if intento is not None:
        db.delete(intento)
    db.delete(usuario)  # las tablas hijas se borran en cascada
    db.commit()
    fotos_storage.borrar(archivos)
    return email, nombre
