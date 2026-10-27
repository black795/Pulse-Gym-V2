from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ahora


class IntentoLogin(Base):
    """Cuenta los intentos fallidos POR CORREO (exista o no). Así, un correo inexistente se comporta
    igual que uno real y nadie puede descubrir quién está registrado."""

    __tablename__ = "intento_login"

    email: Mapped[str] = mapped_column(String(120), primary_key=True)
    fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora, server_default=func.now())


class RecuperacionPassword(Base):
    """Enlace de recuperación: vence a los 30 minutos y se usa una sola vez. Solo se guarda su hash."""

    __tablename__ = "recuperacion_password"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expira_at: Mapped[datetime] = mapped_column(DateTime)
    usado_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())
