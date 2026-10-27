from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.catalogo import AlternativaOut, EjercicioFichaOut, EjercicioResumenOut, GrupoOut, MaquinaOut
from app.services import catalogo_service as svc
from app.services import gym_service, lesion_service

router = APIRouter(prefix="/catalogo", tags=["Catálogo"])


@router.get("/grupos-musculares", response_model=list[GrupoOut])
def grupos(db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return [GrupoOut(codigo=g.codigo, nombre=g.nombre) for g in svc.grupos(db)]


@router.get("/maquinas", response_model=list[MaquinaOut])
def maquinas(
    q: str | None = Query(default=None, max_length=60, description="Busca por nombre u otro nombre común (PG-09)."),
    grupo: str | None = Query(default=None, max_length=30, description="Código del músculo principal."),
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    principales = svc.musculos_principales(db)
    return [svc.a_maquina_out(db, m, principales) for m in svc.buscar_maquinas(db, q=q, grupo=grupo)]


@router.get("/ejercicios", response_model=list[EjercicioResumenOut])
def ejercicios(
    grupo: str | None = None,
    categoria: str | None = Query(default=None, pattern="^(maquina|peso_libre|sin_equipo)$"),
    maquina: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(usuario_actual),
):
    return [svc.a_resumen(e) for e in svc.listar_ejercicios(db, grupo=grupo, categoria=categoria, maquina=maquina)]


@router.get("/ejercicios/{ejercicio_id}", response_model=EjercicioFichaOut)
def ficha(ejercicio_id: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return svc.a_ficha(svc.obtener_ejercicio(db, ejercicio_id))


@router.get("/ejercicios/{ejercicio_id}/alternativas", response_model=list[AlternativaOut])
def alternativas(
    ejercicio_id: int,
    maquinas: str | None = Query(default=None, description="Códigos separados por coma de las máquinas disponibles."),
    gym_id: int | None = Query(default=None, description="Usa lo disponible hoy en este gym (sin malogradas ni retiradas)."),
    limite: int = Query(default=12, ge=1, le=100),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """Reemplazos del ejercicio, respetando las lesiones del usuario."""
    disponibles = {c.strip().upper() for c in maquinas.split(",") if c.strip()} if maquinas else None
    if gym_id is not None:
        disponibles = gym_service.codigos_disponibles(gym_service.obtener(db, usuario, gym_id))
    return svc.alternativas(
        db, svc.obtener_ejercicio(db, ejercicio_id),
        zonas=lesion_service.zonas_por_estado(usuario), maquinas_disponibles=disponibles, limite=limite,
    )
