from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registra las tablas)
from app.api.routes import auth, catalogo, fotos, gyms, lesiones, perfil, plan
from app.core.config import get_settings
from app.core.errores_validacion import manejar_validacion
from app.db.base import Base
from app.db.seed import sembrar_catalogo_si_vacio, sembrar_demo
from app.db.session import SessionLocal, engine
from app.services.errores import ErrorNegocio


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = get_settings()
    cfg.validar_para_produccion()
    Base.metadata.create_all(engine)  # crea las tablas que falten (más adelante: migraciones con Alembic)
    with SessionLocal() as db:
        sembrar_catalogo_si_vacio(db)
        if cfg.seed_demo:
            sembrar_demo(db)
    yield


app = FastAPI(title="Pulse Gym API", version="0.4.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_lista,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(ErrorNegocio)
async def manejar_error_negocio(_: Request, exc: ErrorNegocio):
    contenido = {"detail": exc.mensaje}
    if exc.codigo:
        contenido["codigo"] = exc.codigo
    return JSONResponse(status_code=exc.status, content=contenido)


app.add_exception_handler(RequestValidationError, manejar_validacion)

for r in (auth.router, perfil.router, lesiones.router, catalogo.router, gyms.router, fotos.router, plan.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["Sistema"])
def health():
    return {"estado": "ok"}
