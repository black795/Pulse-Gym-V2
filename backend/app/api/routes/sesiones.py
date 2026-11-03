from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.sesion import IniciarSesionIn, MotivoReemplazo, OpcionesReemplazoOut, ReemplazoIn, SerieIn, SesionOut
from app.services import sesion_service

router = APIRouter(prefix="/sesiones", tags=["Sesión en vivo"])

Numero = Path(ge=1, le=20, description="Número de la serie (1, 2, 3…).")


@router.get("/actual", response_model=SesionOut | None)
def actual(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """La rutina en curso, si hay una (para continuarla después de cerrar la app). Si no, `null`."""
    s = sesion_service.en_curso(db, usuario)
    return sesion_service.a_out(db, usuario, s) if s else None


@router.post("", response_model=SesionOut, status_code=status.HTTP_201_CREATED)
def iniciar(datos: IniciarSesionIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-30: inicia la sesión de hoy ya adaptada al gym y la congela. Solo una a la vez (`codigo: sesion_en_curso`)."""
    s = sesion_service.iniciar(db, usuario, datos)
    return sesion_service.a_out(db, usuario, s)


@router.get("/{sesion_id}", response_model=SesionOut)
def ver(sesion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """La sesión (en curso o terminada, con su resumen)."""
    return sesion_service.a_out(db, usuario, sesion_service.obtener(db, usuario, sesion_id))


@router.delete("/{sesion_id}", status_code=status.HTTP_204_NO_CONTENT)
def descartar(sesion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Descarta una sesión en curso iniciada por error."""
    sesion_service.descartar(db, usuario, sesion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{sesion_id}/ejercicios/{se_id}/series/{numero}", response_model=SesionOut)
def registrar_serie(datos: SerieIn, sesion_id: int, se_id: int, numero: int = Numero,
                    db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-35: guarda o corrige una serie (repetir el pedido no la duplica). Marca los récords (PG-40)."""
    return sesion_service.a_out(db, usuario, sesion_service.registrar_serie(db, usuario, sesion_id, se_id, numero, datos))


@router.delete("/{sesion_id}/ejercicios/{se_id}/series/{numero}", response_model=SesionOut)
def borrar_serie(sesion_id: int, se_id: int, numero: int = Numero,
                 db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Deshace una serie marcada por error."""
    return sesion_service.a_out(db, usuario, sesion_service.borrar_serie(db, usuario, sesion_id, se_id, numero))


@router.get("/{sesion_id}/ejercicios/{se_id}/reemplazos", response_model=OpcionesReemplazoOut)
def reemplazos(
    sesion_id: int, se_id: int,
    motivo: MotivoReemplazo = Query(description="maquina_ocupada (PG-29) o molestia_dolor (PG-22)"),
    zona: str | None = Query(default=None, description="Con molestia_dolor: la zona que molesta (ej. rodilla)."),
    db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual),
):
    """Reemplazos posibles para hoy: otra máquina libre de tu gym → peso libre → sin equipo, siempre seguros."""
    return sesion_service.opciones_reemplazo(db, usuario, sesion_id, se_id, motivo, zona)


@router.post("/{sesion_id}/ejercicios/{se_id}/reemplazar", response_model=SesionOut)
def reemplazar(datos: ReemplazoIn, sesion_id: int, se_id: int,
               db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Cambia el ejercicio solo en esta sesión; tu plan semanal no cambia. Con `guardar_lesion` (PG-22) la molestia
    se guarda en tus lesiones y el próximo plan la tiene en cuenta."""
    return sesion_service.a_out(db, usuario, sesion_service.reemplazar(db, usuario, sesion_id, se_id, datos))


@router.post("/{sesion_id}/finalizar", response_model=SesionOut)
def finalizar(sesion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-37: termina la sesión y la califica (completa o parcial). Tocarlo dos veces no cambia nada."""
    return sesion_service.a_out(db, usuario, sesion_service.finalizar(db, usuario, sesion_id))
