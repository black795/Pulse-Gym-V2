"""PG-49: registro de cada llamada a la IA (para límites diarios, costo estimado y para auditar los rechazos de PG-26)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, ahora


class LlamadaIA(Base):
    __tablename__ = "llamada_ia"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Si se borra la cuenta, el registro queda anónimo: sirve para el costo total del equipo.
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"), index=True)
    tipo: Mapped[str] = mapped_column(String(15))  # foto | plan | adaptacion | busqueda_web
    modelo: Mapped[str] = mapped_column(String(60))
    # ok | rechazada (la respuesta no pasó la validación) | error (falló, tardó o no se entendió)
    # | copia (pedido duplicado porque el primero tardaba; se usó la respuesta que llegó antes)
    resultado: Mapped[str] = mapped_column(String(10))
    detalle: Mapped[str | None] = mapped_column(String(500))  # PG-26: motivo de cada rechazo
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0)
    tokens_salida: Mapped[int] = mapped_column(Integer, default=0)
    costo_usd: Mapped[float] = mapped_column(Float, default=0.0)  # estimado con los precios de la configuración
    duracion_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now(), index=True)
