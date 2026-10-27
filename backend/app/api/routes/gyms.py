from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Usuario
from app.schemas.gym import (
    AgregarMaquinaManualIn, EstadoMaquinaIn, FotoOut, GymCambioIn, GymDetalleOut, GymIn, GymMaquinaOut, GymResumenOut, GymsOut, ImplementoOut,
    ImplementosIn,
)
from app.services import catalogo_service, gym_service as svc, reconocimiento_service

router = APIRouter(tags=["Mis gyms"])


@router.get("/gyms", response_model=GymsOut)
def listar(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Primero el último gym usado (PG-06)."""
    gyms = svc.listar(db, usuario)
    ultimo = next((g.id for g in gyms if g.ultimo_uso_at is not None), None)
    return GymsOut(gyms=[svc.a_resumen(db, usuario, g, ultimo) for g in gyms], maximo=get_settings().gyms_max)


@router.post("/gyms", response_model=GymResumenOut, status_code=status.HTTP_201_CREATED)
def crear(datos: GymIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Nombre obligatorio, ubicación opcional. Arranca vacío. Máximo 5 por usuario."""
    return svc.a_resumen(db, usuario, svc.crear(db, usuario, datos))


@router.get("/gyms/{gym_id}", response_model=GymDetalleOut)
def ver(gym_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return svc.a_detalle(db, usuario, svc.obtener(db, usuario, gym_id))


@router.patch("/gyms/{gym_id}", response_model=GymResumenOut)
def cambiar(gym_id: int, datos: GymCambioIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return svc.a_resumen(db, usuario, svc.cambiar(db, usuario, gym_id, datos))


@router.delete("/gyms/{gym_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(gym_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Borra el gym, su inventario y sus fotos."""
    svc.eliminar(db, usuario, gym_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/gyms/{gym_id}/usar", response_model=GymResumenOut)
def usar(gym_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Marca este gym como el último usado."""
    return svc.a_resumen(db, usuario, svc.marcar_uso(db, usuario, gym_id))


@router.get("/gyms/{gym_id}/disponibles", response_model=list[str])
def disponibles(gym_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Códigos de máquinas que se pueden usar hoy (sin malogradas ni retiradas, con implementos). Para el Sprint 3."""
    return sorted(svc.codigos_disponibles(svc.obtener(db, usuario, gym_id)))


# ---------------- Implementos (PG-14) ----------------
@router.get("/implementos", response_model=list[ImplementoOut])
def implementos(_: Usuario = Depends(usuario_actual)):
    return [ImplementoOut(codigo=c, nombre=n, marcado=False) for c, n, _ in svc.IMPLEMENTOS]


@router.put("/gyms/{gym_id}/implementos", response_model=GymDetalleOut)
def fijar_implementos(gym_id: int, datos: ImplementosIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return svc.a_detalle(db, usuario, svc.fijar_implementos(db, usuario, gym_id, datos))


# ---------------- Inventario (PG-12, PG-13) ----------------
@router.post("/gyms/{gym_id}/maquinas", response_model=GymMaquinaOut, status_code=status.HTTP_201_CREATED)
def agregar_manual(
    gym_id: int, datos: AgregarMaquinaManualIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual),
):
    """Permite agregar una máquina al gym directamente desde el catálogo (sin necesidad de foto)."""
    gm = svc.agregar_maquina_catalogo(db, usuario, gym_id, datos.codigo)
    return svc.a_gym_maquina_out(gm, catalogo_service.musculos_principales(db))


@router.patch("/gyms/{gym_id}/maquinas/{gm_id}", response_model=GymMaquinaOut)
def cambiar_estado(
    gym_id: int, gm_id: int, datos: EstadoMaquinaIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual),
):
    """disponible ⇄ malograda ⇄ retirada. Se guarda la fecha de cada cambio."""
    gm = svc.cambiar_estado(db, usuario, gym_id, gm_id, datos.estado)
    return svc.a_gym_maquina_out(gm, catalogo_service.musculos_principales(db))


@router.delete("/gyms/{gym_id}/maquinas/{gm_id}", status_code=status.HTTP_204_NO_CONTENT)
def quitar(gym_id: int, gm_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Quita una máquina agregada por error (y borra su foto)."""
    svc.quitar_maquina(db, usuario, gym_id, gm_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------- Fotos (PG-07) ----------------
@router.post("/gyms/{gym_id}/fotos", response_model=FotoOut, status_code=status.HTTP_201_CREATED)
def subir_foto(gym_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """JPG, PNG o HEIC de hasta 10 MB. Se guarda reducida a 1280 px y sin metadatos (ubicación GPS)."""
    tope = get_settings().foto_max_mb * 1024 * 1024
    contenido = archivo.file.read(tope + 1)  # se lee 1 byte de más para saber si se pasó del límite
    return reconocimiento_service.a_foto_out(reconocimiento_service.subir(db, usuario, gym_id, contenido))
