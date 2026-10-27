from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Clase madre de todos los modelos (tablas)."""


def ahora() -> datetime:
    """Fecha/hora actual en UTC, sin zona (como TIMESTAMP en PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
