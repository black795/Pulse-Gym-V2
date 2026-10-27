"""PG-05: consentimiento para guardar datos sensibles (peso, medidas, lesiones y, más adelante, fotos)."""
from sqlalchemy.orm import Session

from app.db.base import ahora
from app.models import Lesion, Medicion, Usuario
from app.schemas.perfil import SeccionConsentimiento, TextoConsentimientoOut
from app.services.errores import ErrorNegocio

# Cada vez que cambie el texto, sube la versión: así se sabe qué texto aceptó cada persona.
VERSION_VIGENTE = "2026-10-v1"

# BORRADOR en lenguaje simple. Conviene que lo revise una persona con conocimiento legal antes del lanzamiento.
TEXTO = TextoConsentimientoOut(
    version=VERSION_VIGENTE,
    titulo="Tus datos de salud, en simple",
    secciones=[
        SeccionConsentimiento(
            titulo="Qué guardamos",
            texto="Tu peso, altura, % de grasa, masa muscular, tus lesiones y, más adelante, las fotos que tomes de las máquinas. "
                  "Son datos sensibles porque hablan de tu cuerpo y tu salud.",
        ),
        SeccionConsentimiento(
            titulo="Para qué lo usamos",
            texto="Solo para armar y adaptar tu plan de entrenamiento y mostrarte tu progreso. "
                  "No los usamos para publicidad.",
        ),
        SeccionConsentimiento(
            titulo="Quién lo ve",
            texto="Solo tú. No se comparten con otros usuarios ni con gimnasios.",
        ),
        SeccionConsentimiento(
            titulo="Tú tienes el control",
            texto="Puedes retirar tu consentimiento cuando quieras desde Perfil → Privacidad: borramos tus datos sensibles. "
                  "También puedes eliminar tu cuenta y todos tus datos. "
                  "Si prefieres no aceptar, igual puedes usar la app, pero sin guardar lesiones, medidas ni fotos.",
        ),
    ],
)


def texto() -> TextoConsentimientoOut:
    return TEXTO


def exigir_consentimiento(usuario: Usuario) -> None:
    if not usuario.consentimiento_aceptado:
        raise ErrorNegocio(
            "Para guardar datos de salud necesitamos tu consentimiento. Puedes darlo en Perfil → Privacidad.",
            403, "consentimiento_requerido",
        )


def borrar_datos_sensibles(db: Session, usuario: Usuario) -> None:
    db.query(Medicion).filter(Medicion.usuario_id == usuario.id).delete()
    db.query(Lesion).filter(Lesion.usuario_id == usuario.id).delete()
    usuario.altura_cm = None
    usuario.plan_requiere_regenerar = True  # el plan ya no puede basarse en lesiones ni medidas borradas
    db.expire(usuario, ["mediciones", "lesiones"])


def fijar(db: Session, usuario: Usuario, acepta: bool) -> Usuario:
    if acepta:
        usuario.consentimiento_estado = "aceptado"
        usuario.consentimiento_version = VERSION_VIGENTE
        usuario.consentimiento_at = ahora()
    else:
        # Rechazar o retirar: se borran los datos sensibles que hubiera.
        borrar_datos_sensibles(db, usuario)
        usuario.consentimiento_estado = "rechazado"
        usuario.consentimiento_version = None
        usuario.consentimiento_at = None
    db.commit()
    db.refresh(usuario)
    return usuario
