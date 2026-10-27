from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.plan import DiaSemana, GenerarPlanIn, HoyOut, PlanEstadoOut, UsoIAOut
from app.services import adaptacion_service, ia_uso_service, plan_service

router = APIRouter(tags=["Plan semanal"])


@router.get("/plan", response_model=PlanEstadoOut)
def ver_plan(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """El plan activo. Si tus lesiones cambiaron desde que se armó, se regenera solo antes de mostrarlo (PG-20)."""
    return plan_service.estado(db, usuario, plan_service.vigente(db, usuario))


@router.post("/plan", response_model=PlanEstadoOut, status_code=status.HTTP_201_CREATED)
def generar_plan(datos: GenerarPlanIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Arma el plan (o lo regenera: máximo 3 veces al día, `codigo: limite_regeneraciones`). Tarda menos de 20 s:
    si la IA no responde a tiempo o su plan no pasa la validación, se usa la versión de solo reglas."""
    rutina = plan_service.generar(db, usuario, datos.dias, "regenerar")
    return plan_service.estado(db, usuario, rutina)


@router.get("/hoy", response_model=HoyOut)
def hoy(
    gym_id: int | None = Query(default=None, description="Gym donde estás. Con más de un gym y sin este dato, se pide elegir."),
    dia: DiaSemana | None = Query(default=None, description="Para adelantar otro día del plan."),
    fecha: date | None = Query(default=None, description="Fecha local del celular (AAAA-MM-DD)."),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(usuario_actual),
):
    """PG-28: el día que toca del plan, adaptado a las máquinas disponibles hoy en ese gym."""
    return adaptacion_service.hoy(db, usuario, gym_id=gym_id, dia=dia, fecha=fecha)


@router.get("/ia/uso", response_model=UsoIAOut)
def uso_ia(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-49: cuánto usaste la IA hoy y tus límites diarios."""
    return ia_uso_service.resumen_usuario(db, usuario)
