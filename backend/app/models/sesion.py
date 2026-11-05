"""Sesión en vivo (Sprint 4): sesion_entreno, sesion_ejercicio y serie_registrada.

Idea clave (PG-30): al iniciar, la sesión de hoy se "congela": se copian los ejercicios ya adaptados al gym. Si
después cambia el plan, el inventario o las lesiones, la sesión en curso no se toca. Solo cambia por decisión del
usuario en vivo (máquina ocupada PG-29, molestia PG-22), y esos cambios valen solo para hoy.
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ahora


class SesionEntreno(Base):
    __tablename__ = "sesion_entreno"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    # PG-06: borrar el gym no borra el historial (queda en NULL, y el nombre se guarda aparte).
    gym_id: Mapped[int | None] = mapped_column(ForeignKey("gym.id", ondelete="SET NULL"), index=True)
    rutina_dia_id: Mapped[int | None] = mapped_column(ForeignKey("rutina_dia.id", ondelete="SET NULL"))
    gym_nombre: Mapped[str | None] = mapped_column(String(60))
    dia_semana: Mapped[str] = mapped_column(String(10))  # el día del plan que se hizo (puede ser uno adelantado)
    enfoque: Mapped[str] = mapped_column(String(60))
    fecha: Mapped[date] = mapped_column(Date)  # día local del celular
    inicio_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())
    fin_at: Mapped[datetime | None] = mapped_column(DateTime)
    duracion_estimada_seg: Mapped[int] = mapped_column(Integer, default=0)
    estado: Mapped[str] = mapped_column(String(10), default="en_curso")  # en_curso | completa | parcial
    # PG-37: solo una sesión completa cuenta para la asistencia (y la racha del Sprint 5).
    cuenta_asistencia: Mapped[bool] = mapped_column(Boolean, default=False)
    # Se cerró sola porque el usuario la dejó abierta (no tocó "Finalizar").
    cerrada_auto: Mapped[bool] = mapped_column(Boolean, default=False)

    ejercicios: Mapped[list["SesionEjercicio"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="SesionEjercicio.orden", lazy="selectin",
    )


class SesionEjercicio(Base):
    """Un ejercicio de la sesión, ya adaptado al gym del día. Las series/reps/descanso se copian del plan."""

    __tablename__ = "sesion_ejercicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[int] = mapped_column(ForeignKey("sesion_entreno.id", ondelete="CASCADE"), index=True)
    rutina_ejercicio_id: Mapped[int | None] = mapped_column(ForeignKey("rutina_ejercicio.id", ondelete="SET NULL"))
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicio.id", ondelete="RESTRICT"), index=True)
    gym_maquina_id: Mapped[int | None] = mapped_column(ForeignKey("gym_maquina.id", ondelete="SET NULL"))
    # El ejercicio al que reemplaza (del plan o de un cambio anterior), para explicar el cambio.
    reemplaza_id: Mapped[int | None] = mapped_column(ForeignKey("ejercicio.id", ondelete="SET NULL"))
    orden: Mapped[int] = mapped_column(Integer)
    series: Mapped[int] = mapped_column(Integer)
    reps_min: Mapped[int] = mapped_column(Integer)
    reps_max: Mapped[int] = mapped_column(Integer)
    descanso_seg: Mapped[int] = mapped_column(Integer, default=120)
    # plan_original | adaptado_gym | maquina_ocupada | sin_equipo | molestia_dolor
    motivo: Mapped[str] = mapped_column(String(20), default="plan_original")
    nota: Mapped[str | None] = mapped_column(String(300))  # por qué cambió
    precaucion: Mapped[bool] = mapped_column(Boolean, default=False)
    # Reemplazado en vivo después de hacer algunas series: queda cerrado con lo que se hizo.
    cerrado: Mapped[bool] = mapped_column(Boolean, default=False)

    ejercicio: Mapped["Ejercicio"] = relationship(lazy="joined", foreign_keys=[ejercicio_id])
    reemplaza: Mapped["Ejercicio | None"] = relationship(lazy="joined", foreign_keys=[reemplaza_id])
    series_hechas: Mapped[list["SerieRegistrada"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="SerieRegistrada.numero_serie", lazy="selectin",
    )


class SerieRegistrada(Base):
    __tablename__ = "serie_registrada"
    __table_args__ = (UniqueConstraint("sesion_ejercicio_id", "numero_serie"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_ejercicio_id: Mapped[int] = mapped_column(ForeignKey("sesion_ejercicio.id", ondelete="CASCADE"), index=True)
    numero_serie: Mapped[int] = mapped_column(Integer)
    peso_kg: Mapped[float] = mapped_column(Float, default=0)
    repeticiones: Mapped[int] = mapped_column(Integer)
    es_record: Mapped[bool] = mapped_column(Boolean, default=False)  # PG-40
    completada_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())


from app.models.catalogo import Ejercicio  # noqa: E402  (al final para evitar importación circular)
