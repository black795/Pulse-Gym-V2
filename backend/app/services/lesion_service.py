"""PG-19: registro de lesiones."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import ahora
from app.models import Lesion, Usuario, ZonaLesion
from app.schemas.lesion import LesionCambioIn, LesionIn, LesionOut, ZonaOut
from app.services import consentimiento_service
from app.services.errores import ErrorNegocio

AVISO_MEDICO = (
    "Pulse Gym no reemplaza a un médico. Si sientes dolor fuerte, mareo o algo que te preocupa, "
    "detente y consulta a un profesional de la salud."
)

# Una lesión en estos estados limita los ejercicios que la IA puede proponer.
ESTADOS_QUE_LIMITAN = ("activa", "reintroduccion")


def a_out(lesion: Lesion) -> LesionOut:
    return LesionOut(
        id=lesion.id, zona=ZonaOut(codigo=lesion.zona.codigo, nombre=lesion.zona.nombre), tipo=lesion.tipo,
        duele_con_carga=lesion.duele_con_carga, descripcion=lesion.descripcion, estado=lesion.estado,
        created_at=lesion.created_at, recuperada_at=lesion.recuperada_at,
    )


def zonas(db: Session) -> list[ZonaLesion]:
    return list(db.scalars(select(ZonaLesion).order_by(ZonaLesion.id)))


def _zona(db: Session, codigo: str) -> ZonaLesion:
    z = db.scalar(select(ZonaLesion).where(ZonaLesion.codigo == codigo))
    if z is None:
        validas = ", ".join(zn.codigo for zn in zonas(db))
        raise ErrorNegocio(f"La zona «{codigo}» no existe. Opciones: {validas}.", 400)
    return z


def listar(usuario: Usuario, incluir_recuperadas: bool = True) -> list[Lesion]:
    # Las recuperadas quedan en el historial.
    return [l for l in usuario.lesiones if incluir_recuperadas or l.estado != "recuperada"]


def zonas_por_estado(usuario: Usuario) -> dict[str, str]:
    """Zona → estado de la lesión que hoy limita el entrenamiento ("activa" o "reintroduccion").
    Si hay dos lesiones en la misma zona, manda la más restrictiva (activa)."""
    zonas: dict[str, str] = {}
    for l in usuario.lesiones:
        if l.estado in ESTADOS_QUE_LIMITAN and zonas.get(l.zona.codigo) != "activa":
            zonas[l.zona.codigo] = l.estado
    return zonas


def crear(db: Session, usuario: Usuario, datos: LesionIn) -> Lesion:
    consentimiento_service.exigir_consentimiento(usuario)
    lesion = Lesion(
        usuario_id=usuario.id, zona_id=_zona(db, datos.zona).id, tipo=datos.tipo,
        duele_con_carga=datos.duele_con_carga, descripcion=(datos.descripcion or "").strip() or None,
        estado=datos.estado,
    )
    db.add(lesion)
    usuario.plan_requiere_regenerar = True  # PG-19 → PG-20: el plan se marca para regenerarse
    db.commit()
    db.refresh(lesion)
    db.expire(usuario, ["lesiones"])
    return lesion


def _de_usuario(db: Session, usuario: Usuario, lesion_id: int) -> Lesion:
    lesion = db.get(Lesion, lesion_id)
    if lesion is None or lesion.usuario_id != usuario.id:  # no se distingue "no existe" de "no es tuya"
        raise ErrorNegocio("Lesión no encontrada.", 404)
    return lesion


def cambiar(db: Session, usuario: Usuario, lesion_id: int, datos: LesionCambioIn) -> Lesion:
    consentimiento_service.exigir_consentimiento(usuario)
    lesion = _de_usuario(db, usuario, lesion_id)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise ErrorNegocio("No enviaste ningún cambio.", 400)

    if "zona" in cambios:
        lesion.zona_id = _zona(db, cambios["zona"]).id
    for campo in ("tipo", "duele_con_carga"):
        if campo in cambios and cambios[campo] is not None:
            setattr(lesion, campo, cambios[campo])
    if "descripcion" in cambios:
        lesion.descripcion = (cambios["descripcion"] or "").strip() or None
    if cambios.get("estado"):
        lesion.estado = cambios["estado"]
        lesion.recuperada_at = ahora() if lesion.estado == "recuperada" else None

    usuario.plan_requiere_regenerar = True
    db.commit()
    db.refresh(lesion)
    db.expire(usuario, ["lesiones"])
    return lesion
