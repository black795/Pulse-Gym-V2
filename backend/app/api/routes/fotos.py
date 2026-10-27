from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.session import get_db
from app.models import FotoMaquina, Usuario
from app.schemas.gym import ConfirmarIn, ConfirmarOut, FotoOut, ReconocimientoOut
from app.services import fotos_storage, reconocimiento_service as svc
from app.services.errores import ErrorNegocio

router = APIRouter(prefix="/fotos", tags=["Fotos e IA"])


@router.post("/{foto_id}/reconocer", response_model=ReconocimientoOut)
def reconocer(foto_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-08: la IA compara la foto con el catálogo y devuelve hasta 3 máquinas con su confianza.
    Si falla o tarda más de 15 s responde 503 (`codigo: ia_fallo`): la app ofrece reintentar o elegir a mano."""
    return svc.reconocer(db, usuario, foto_id)


@router.post("/{foto_id}/confirmar", response_model=ConfirmarOut)
def confirmar(foto_id: int, datos: ConfirmarIn, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """PG-09/PG-12: agrega la máquina al gym. Si ya estaba responde 409 (`codigo: ya_en_inventario`);
    reenviar con `reemplazar_foto: true` actualiza su foto."""
    return svc.confirmar(db, usuario, foto_id, datos)


@router.post("/{foto_id}/ninguna", response_model=FotoOut)
def ninguna(foto_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """«Ninguna es»: queda pendiente para la búsqueda en internet (PG-10, Sprint 5)."""
    return svc.a_foto_out(svc.ninguna(db, usuario, foto_id))


@router.delete("/{foto_id}", status_code=status.HTTP_204_NO_CONTENT)
def descartar(foto_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    svc.descartar(db, usuario, foto_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{foto_id}/imagen", include_in_schema=False)
def imagen(foto_id: int, exp: int = Query(...), firma: str = Query(..., max_length=64), db: Session = Depends(get_db)):
    """PG-48: la foto solo se ve con el enlace temporal firmado que la API le dio a su dueño (vence en 1 hora).
    No pide token porque las etiquetas <img> no pueden enviarlo; la firma cumple ese papel."""
    if not fotos_storage.firma_valida(foto_id, exp, firma):
        raise ErrorNegocio("El enlace de la foto venció. Vuelve a abrir la pantalla.", 403, "enlace_vencido")
    foto = db.get(FotoMaquina, foto_id)
    if foto is None or not foto.archivo:
        raise ErrorNegocio("Foto no encontrada.", 404)
    return FileResponse(
        fotos_storage.ruta(foto.archivo), media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )
