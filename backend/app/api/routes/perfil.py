from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import Usuario
from app.schemas.perfil import (
    ConsentimientoEstadoOut, ConsentimientoIn, MedicionOut, PerfilIn, PerfilOut, TextoConsentimientoOut,
)
from app.services import consentimiento_service, correo, perfil_service, usuario_service

router = APIRouter(tags=["Perfil y privacidad"])


@router.get("/perfil", response_model=PerfilOut)
def ver_perfil(usuario: Usuario = Depends(usuario_actual)):
    return perfil_service.obtener(usuario)


@router.put("/perfil", response_model=PerfilOut)
def guardar_perfil(datos: PerfilIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Guarda solo los datos que envíes (cada pantalla del registro manda los suyos)."""
    return perfil_service.obtener(perfil_service.actualizar(db, usuario, datos))


@router.get("/mediciones", response_model=list[MedicionOut])
def mediciones(usuario: Usuario = Depends(usuario_actual)):
    return [
        MedicionOut(fecha=m.fecha, peso_kg=m.peso_kg, grasa_pct=m.grasa_pct, masa_muscular_kg=m.masa_muscular_kg)
        for m in usuario.mediciones
    ]


# ---------------- Consentimiento (PG-05) ----------------
@router.get("/consentimiento/texto", response_model=TextoConsentimientoOut)
def texto_consentimiento():
    return consentimiento_service.texto()


@router.get("/consentimiento", response_model=ConsentimientoEstadoOut)
def estado_consentimiento(usuario: Usuario = Depends(usuario_actual)):
    return perfil_service.obtener(usuario).consentimiento


@router.put("/consentimiento", response_model=ConsentimientoEstadoOut)
def fijar_consentimiento(datos: ConsentimientoIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """acepta=true: guarda fecha, hora y versión del texto. acepta=false: rechaza o RETIRA el consentimiento
    y borra de inmediato las mediciones, lesiones y la altura."""
    consentimiento_service.fijar(db, usuario, datos.acepta)
    return perfil_service.obtener(usuario).consentimiento


# ---------------- Borrar cuenta (PG-05) ----------------
@router.delete("/cuenta", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(tareas: BackgroundTasks, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Elimina la cuenta y todos sus datos. Envía un correo de confirmación."""
    email, nombre = usuario_service.eliminar_cuenta(db, usuario)
    tareas.add_task(correo.correo_cuenta_eliminada, email, nombre)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
