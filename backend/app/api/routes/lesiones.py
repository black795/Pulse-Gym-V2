from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.lesion import LesionCambioIn, LesionesOut, LesionIn, LesionOut, ZonaOut
from app.services import lesion_service as svc

router = APIRouter(tags=["Lesiones"])


@router.get("/zonas-lesion", response_model=list[ZonaOut])
def zonas(db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return [ZonaOut(codigo=z.codigo, nombre=z.nombre) for z in svc.zonas(db)]


@router.get("/lesiones", response_model=LesionesOut)
def listar(incluir_recuperadas: bool = True, usuario: Usuario = Depends(usuario_actual)):
    return LesionesOut(
        aviso=svc.AVISO_MEDICO,
        lesiones=[svc.a_out(l) for l in svc.listar(usuario, incluir_recuperadas)],
    )


@router.post("/lesiones", response_model=LesionOut, status_code=status.HTTP_201_CREATED)
def crear(datos: LesionIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Se puede llamar desde el perfil o durante la sesión de entrenamiento. Permite varias lesiones a la vez."""
    return svc.a_out(svc.crear(db, usuario, datos))


@router.patch("/lesiones/{lesion_id}", response_model=LesionOut)
def cambiar(lesion_id: int, datos: LesionCambioIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return svc.a_out(svc.cambiar(db, usuario, lesion_id, datos))
