from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Usuario
from app.schemas.auth import LoginIn, MensajeOut, RecuperarIn, RegistroIn, RestablecerIn, SesionOut, UsuarioOut
from app.services import auth_service, correo, usuario_service

router = APIRouter(prefix="/auth", tags=["Cuenta"])


def _sesion(usuario: Usuario) -> SesionOut:
    return SesionOut(
        access_token=auth_service.emitir_token(usuario),
        expira_en_dias=get_settings().sesion_dias,
        usuario=usuario_service.a_usuario_out(usuario),
    )


@router.post("/login", response_model=SesionOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    return _sesion(auth_service.autenticar(db, datos.email, datos.password))


@router.post("/registro", response_model=SesionOut, status_code=status.HTTP_201_CREATED)
def registro(datos: RegistroIn, db: Session = Depends(get_db)):
    """Crea una cuenta. No hay roles: todas las cuentas son de usuario."""
    usuario = usuario_service.crear_usuario(db, nombre=datos.nombre, email=datos.email, password=datos.password)
    return _sesion(usuario)


@router.get("/me", response_model=UsuarioOut)
def yo(usuario: Usuario = Depends(usuario_actual)):
    return usuario_service.a_usuario_out(usuario)


@router.post("/recuperar", response_model=MensajeOut)
def recuperar(datos: RecuperarIn, tareas: BackgroundTasks, db: Session = Depends(get_db)):
    """Siempre responde lo mismo: no revela si el correo está registrado."""
    cfg = get_settings()
    resultado = auth_service.solicitar_recuperacion(db, datos.email)
    if resultado is not None:
        usuario, token = resultado
        enlace = f"{cfg.url_app.rstrip('/')}/restablecer?token={token}"
        # El correo se envía "en segundo plano" para que la respuesta tarde igual exista o no la cuenta.
        tareas.add_task(correo.correo_recuperacion, usuario.email, usuario.nombre, enlace, cfg.recuperacion_minutos)
    return MensajeOut(mensaje="Si ese correo está registrado, te enviamos un enlace para restablecer tu contraseña.")


@router.post("/restablecer", response_model=MensajeOut)
def restablecer(datos: RestablecerIn, db: Session = Depends(get_db)):
    auth_service.restablecer_password(db, datos.token, datos.password)
    return MensajeOut(mensaje="Listo. Ya puedes iniciar sesión con tu nueva contraseña.")
