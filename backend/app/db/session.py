from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_url = get_settings().database_url
_es_sqlite = _url.startswith("sqlite")
# SQLite necesita este parámetro para usarse desde varios hilos; PostgreSQL no.
_args = {"check_same_thread": False} if _es_sqlite else {}

engine = create_engine(_url, connect_args=_args, pool_pre_ping=True)

if _es_sqlite:

    @event.listens_for(engine, "connect")
    def _activar_llaves_foraneas(conexion, _):
        # SQLite las ignora por defecto; sin esto, borrar una cuenta no borraría sus datos en cascada.
        conexion.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Abre una sesión por petición y la cierra siempre al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
