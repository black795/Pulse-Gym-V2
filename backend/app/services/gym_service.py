"""Mis gyms: registrar (PG-06), inventario sin duplicados (PG-12), estados (PG-13) e implementos (PG-14)."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import FotoMaquina, GrupoMuscular, Gym, GymMaquina, MaquinaCatalogo, Usuario
from app.schemas.gym import (
    GymCambioIn, GymDetalleOut, GymIn, GymMaquinaOut, GymResumenOut, ImplementoOut, ImplementosIn, MaquinaOpcionOut,
)
from app.services import catalogo_service, fotos_storage
from app.services.errores import ErrorNegocio

# PG-14: lista inicial de implementos. El tercer valor son las máquinas del catálogo que "habilita" cada uno,
# para que el plan (Sprint 3) sepa qué ejercicios se pueden hacer sin haberlos fotografiado.
IMPLEMENTOS: list[tuple[str, str, list[str]]] = [
    ("mancuernas", "Mancuernas", ["MANCUERNAS"]),
    ("barra", "Barra", ["BARRA_OLIMPICA", "BARRA_Z"]),
    ("discos", "Discos", []),
    ("banco_plano", "Banco plano", ["BANCO_PLANO"]),
    ("banco_inclinable", "Banco inclinable", ["BANCO_INCLINADO"]),
    ("rack", "Rack", ["RACK_SENTADILLA"]),
    ("barra_dominadas", "Barra de dominadas", ["BARRA_DOMINADAS"]),
    ("kettlebell", "Kettlebell", ["KETTLEBELL"]),
    ("bandas", "Bandas elásticas", []),
    ("colchoneta", "Colchoneta", []),
]
CODIGOS_IMPLEMENTOS = [c for c, _, _ in IMPLEMENTOS]


# ---------------- Gyms (PG-06) ----------------
def listar(db: Session, usuario: Usuario) -> list[Gym]:
    # Primero el último usado; los nunca usados, por fecha de creación.
    return list(db.scalars(
        select(Gym).where(Gym.usuario_id == usuario.id)
        .order_by(Gym.ultimo_uso_at.is_(None), Gym.ultimo_uso_at.desc(), Gym.created_at, Gym.id)
    ))


def obtener(db: Session, usuario: Usuario, gym_id: int) -> Gym:
    gym = db.get(Gym, gym_id)
    if gym is None or gym.usuario_id != usuario.id:  # el gym de otra persona "no existe" para ti
        raise ErrorNegocio("Gym no encontrado.", 404)
    return gym


def _nombre_repetido(db: Session, usuario: Usuario, nombre: str, excepto_id: int | None = None) -> bool:
    consulta = select(Gym.id).where(Gym.usuario_id == usuario.id, func.lower(Gym.nombre) == nombre.lower())
    if excepto_id is not None:
        consulta = consulta.where(Gym.id != excepto_id)
    return db.scalar(consulta) is not None


def crear(db: Session, usuario: Usuario, datos: GymIn) -> Gym:
    maximo = get_settings().gyms_max
    if db.scalar(select(func.count()).select_from(Gym).where(Gym.usuario_id == usuario.id)) >= maximo:
        raise ErrorNegocio(f"Puedes registrar hasta {maximo} gyms. Elimina uno para agregar otro.", 400, "limite_gyms")
    if _nombre_repetido(db, usuario, datos.nombre):
        raise ErrorNegocio("Ya tienes un gym con ese nombre.", 409, "gym_duplicado")
    gym = Gym(usuario_id=usuario.id, nombre=datos.nombre, ubicacion=datos.ubicacion, implementos=[])
    db.add(gym)
    db.commit()
    db.refresh(gym)
    return gym


def cambiar(db: Session, usuario: Usuario, gym_id: int, datos: GymCambioIn) -> Gym:
    gym = obtener(db, usuario, gym_id)
    enviados = datos.model_fields_set
    if "nombre" in enviados:
        if not datos.nombre:
            raise ErrorNegocio("El nombre del gym es obligatorio.", 422)
        if _nombre_repetido(db, usuario, datos.nombre, excepto_id=gym.id):
            raise ErrorNegocio("Ya tienes un gym con ese nombre.", 409, "gym_duplicado")
        gym.nombre = datos.nombre
    if "ubicacion" in enviados:
        gym.ubicacion = datos.ubicacion
    db.commit()
    return gym


def eliminar(db: Session, usuario: Usuario, gym_id: int) -> None:
    """Borra el gym, su inventario y sus fotos (PG-48). El historial de sesiones (Sprint 4) no se borra:
    sesion_entreno.gym_id queda en NULL."""
    gym = obtener(db, usuario, gym_id)
    archivos = [f.archivo for f in gym.fotos if f.archivo]
    db.delete(gym)
    db.commit()
    fotos_storage.borrar(archivos)


def marcar_uso(db: Session, usuario: Usuario, gym_id: int) -> Gym:
    gym = obtener(db, usuario, gym_id)
    gym.ultimo_uso_at = ahora()
    db.commit()
    return gym


# ---------------- Implementos (PG-14) ----------------
def fijar_implementos(db: Session, usuario: Usuario, gym_id: int, datos: ImplementosIn) -> Gym:
    gym = obtener(db, usuario, gym_id)
    desconocidos = set(datos.implementos) - set(CODIGOS_IMPLEMENTOS)
    if desconocidos:
        raise ErrorNegocio(f"Implemento no válido: {', '.join(sorted(desconocidos))}.", 400)
    gym.implementos = [c for c in CODIGOS_IMPLEMENTOS if c in datos.implementos]  # lista nueva → SQLAlchemy ve el cambio
    # El peso máximo solo tiene sentido si hay mancuernas.
    gym.mancuernas_max_kg = datos.mancuernas_max_kg if "mancuernas" in gym.implementos else None
    db.commit()
    return gym


# ---------------- Inventario (PG-12, PG-13) ----------------
def obtener_maquina(db: Session, usuario: Usuario, gym_id: int, gm_id: int) -> GymMaquina:
    gym = obtener(db, usuario, gym_id)
    gm = db.get(GymMaquina, gm_id)
    if gm is None or gm.gym_id != gym.id:
        raise ErrorNegocio("Esa máquina no está en este gym.", 404)
    return gm


def registrar_estado(gm: GymMaquina, estado: str) -> None:
    """Cambia el estado y guarda la fecha del cambio (PG-13)."""
    momento = ahora()
    gm.estado = estado
    gm.estado_at = momento
    gm.historial_estados = [*(gm.historial_estados or []), {"estado": estado, "fecha": momento.isoformat(timespec="seconds")}]


def agregar_maquina_catalogo(db: Session, usuario: Usuario, gym_id: int, codigo: str) -> GymMaquina:
    """Permite agregar una máquina al inventario directamente desde el catálogo, sin pasar por foto."""
    gym = obtener(db, usuario, gym_id)
    codigo_limpio = codigo.strip().upper()
    maquina = db.scalar(select(MaquinaCatalogo).where(
        MaquinaCatalogo.codigo == codigo_limpio, MaquinaCatalogo.activa.is_(True),
    ))
    if maquina is None:
        raise ErrorNegocio("Esa máquina no existe en el catálogo o no está activa.", 404, "maquina_no_encontrada")

    existente = db.scalar(
        select(GymMaquina).where(GymMaquina.gym_id == gym.id, GymMaquina.maquina_id == maquina.id)
    )
    if existente is not None:
        if existente.estado == "retirada":
            registrar_estado(existente, "disponible")
            db.commit()
            db.refresh(existente)
            return existente
        raise ErrorNegocio("Esta máquina ya está en el inventario de tu gym.", 409, "ya_en_inventario")

    gm = GymMaquina(gym_id=gym.id, maquina_id=maquina.id, foto_id=None, historial_estados=[])
    registrar_estado(gm, "disponible")
    db.add(gm)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErrorNegocio("Esta máquina ya está en el inventario de tu gym.", 409, "ya_en_inventario")
    db.refresh(gm)
    return gm


def cambiar_estado(db: Session, usuario: Usuario, gym_id: int, gm_id: int, estado: str) -> GymMaquina:
    gm = obtener_maquina(db, usuario, gym_id, gm_id)
    if gm.estado != estado:
        registrar_estado(gm, estado)
        db.commit()
    return gm


def descartar_foto(db: Session, foto: FotoMaquina) -> str | None:
    """Borra el archivo de una foto pero conserva la fila con lo que dijo la IA (sirve para calibrar).
    Devuelve el archivo a borrar DESPUÉS del commit."""
    archivo = foto.archivo or None
    if foto.reconocimientos or foto.eleccion:
        foto.archivo = ""
        foto.estado = "descartada"
    else:
        db.delete(foto)
    return archivo


def quitar_maquina(db: Session, usuario: Usuario, gym_id: int, gm_id: int) -> None:
    """PG-12: eliminar una máquina agregada por error (y su foto)."""
    gm = obtener_maquina(db, usuario, gym_id, gm_id)
    foto = gm.foto
    db.delete(gm)
    db.flush()
    archivo = descartar_foto(db, foto) if foto is not None else None
    db.commit()
    fotos_storage.borrar([archivo] if archivo else [])


def codigos_disponibles(gym: Gym) -> set[str]:
    """Lo que se puede usar HOY en este gym: máquinas disponibles (no malogradas ni retiradas) + implementos.
    Lo consume la adaptación de la sesión (Sprint 3) y la búsqueda de alternativas."""
    codigos = {gm.maquina.codigo for gm in gym.maquinas if gm.estado == "disponible" and gm.maquina and gm.maquina.activa}
    for codigo, _, habilita in IMPLEMENTOS:
        if codigo in (gym.implementos or []):
            codigos.update(habilita)
    return codigos


# ---------------- Conversión a respuestas ----------------
def opcion(m: MaquinaCatalogo, principales: dict[int, GrupoMuscular]) -> MaquinaOpcionOut:
    principal = principales.get(m.id)
    return MaquinaOpcionOut(
        codigo=m.codigo, nombre=m.nombre, tipo=m.tipo, foto_ref=m.fotos[0].url if m.fotos else None,
        musculo_principal=principal.nombre if principal else None,
    )


def a_gym_maquina_out(gm: GymMaquina, principales: dict[int, GrupoMuscular]) -> GymMaquinaOut:
    foto = gm.foto
    return GymMaquinaOut(
        id=gm.id, maquina=opcion(gm.maquina, principales), estado=gm.estado, estado_at=gm.estado_at,  # type: ignore[arg-type]
        foto_url=fotos_storage.enlace_temporal(foto.id) if foto is not None and foto.archivo else None,
        agregada_at=gm.agregada_at, historial_estados=list(gm.historial_estados or []),
    )


def _ultimo_usado_id(db: Session, usuario: Usuario) -> int | None:
    return db.scalar(
        select(Gym.id).where(Gym.usuario_id == usuario.id, Gym.ultimo_uso_at.is_not(None))
        .order_by(Gym.ultimo_uso_at.desc()).limit(1)
    )


def a_resumen(db: Session, usuario: Usuario, gym: Gym, ultimo_id: int | None = None) -> GymResumenOut:
    if ultimo_id is None:
        ultimo_id = _ultimo_usado_id(db, usuario)
    return GymResumenOut(
        id=gym.id, nombre=gym.nombre, ubicacion=gym.ubicacion,
        maquinas=sum(1 for gm in gym.maquinas if gm.estado != "retirada"),
        implementos=len(gym.implementos or []), ultimo_uso_at=gym.ultimo_uso_at,
        es_ultimo_usado=gym.id == ultimo_id, created_at=gym.created_at,
    )


def a_detalle(db: Session, usuario: Usuario, gym: Gym) -> GymDetalleOut:
    principales = catalogo_service.musculos_principales(db)
    return GymDetalleOut(
        **a_resumen(db, usuario, gym).model_dump(),
        inventario=[a_gym_maquina_out(gm, principales) for gm in gym.maquinas if gm.maquina is not None],
        lista_implementos=[ImplementoOut(codigo=c, nombre=n, marcado=c in (gym.implementos or [])) for c, n, _ in IMPLEMENTOS],
        mancuernas_max_kg=gym.mancuernas_max_kg,
    )
