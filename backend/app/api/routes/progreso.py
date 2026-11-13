from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.base import ahora
from app.db.session import get_db
from app.models import Usuario
from app.schemas.progreso import AlertasOut, ConstanciaOut, EjercicioDetalleOut, EjerciciosUsadosOut, HistorialOut
from app.services import progreso_service

router = APIRouter(prefix="/progreso", tags=["Progreso"])


@router.get("/constancia", response_model=ConstanciaOut)
def constancia(
    fecha: date | None = Query(default=None, description="Fecha local del celular (AAAA-MM-DD)."),
    db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual),
):
    """PG-38: racha actual y mejor racha, y sesiones completas de la semana y del mes."""
    return progreso_service.constancia(db, usuario, fecha or ahora().date())


@router.get("/historial", response_model=HistorialOut)
def historial(
    pagina: int = Query(default=1, ge=1), por_pagina: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual),
):
    """PG-46: sesiones terminadas (completas y parciales), de la más reciente a la más antigua."""
    return progreso_service.historial(db, usuario, pagina, por_pagina)


FechaLocal = Query(default=None, description="Fecha local del celular (AAAA-MM-DD).")


@router.get("/ejercicios", response_model=EjerciciosUsadosOut)
def ejercicios(fecha: date | None = FechaLocal, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Historial de máquinas y pesos: solo los ejercicios que ya hiciste, con tu último peso, récord (PG-40) y el peso
    sugerido para la próxima vez (PG-41)."""
    return progreso_service.ejercicios_usados(db, usuario, fecha or ahora().date())


@router.get("/ejercicios/{ejercicio_id}", response_model=EjercicioDetalleOut)
def ejercicio(ejercicio_id: int, fecha: date | None = FechaLocal, db: Session = Depends(get_db),
              usuario: Usuario = Depends(usuario_actual)):
    """Evolución de un ejercicio que ya hiciste (404 si nunca lo hiciste) y si estás estancado (PG-43)."""
    return progreso_service.ejercicio_detalle(db, usuario, ejercicio_id, fecha or ahora().date())


@router.get("/alertas", response_model=AlertasOut)
def alertas(fecha: date | None = FechaLocal, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-42: volviste después de una ausencia. PG-43: ejercicios estancados."""
    return progreso_service.alertas(db, usuario, fecha or ahora().date())
