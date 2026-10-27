"""Plan semanal (Sprint 3): rutina (versiones), rutina_dia, rutina_ejercicio y la adaptación del día a un gym.

Idea clave: el plan es la receta (no depende del gym); la adaptación es cómo se hace esa receta hoy en un gym concreto.
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ahora

DIAS_SEMANA = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


class Rutina(Base):
    """Una versión del plan semanal. Nunca se sobrescribe: regenerar crea otra versión y archiva la anterior (PG-31)."""

    __tablename__ = "rutina"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    rutina_anterior_id: Mapped[int | None] = mapped_column(ForeignKey("rutina.id", ondelete="SET NULL"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    estado: Mapped[str] = mapped_column(String(10), default="activa")  # activa | archivada
    # PG-26: "ia" si la IA eligió todo y pasó la validación; "mixto" si algunos días quedaron con la versión de reglas;
    # "reglas" si se usó la versión de solo reglas.
    origen: Mapped[str] = mapped_column(String(10))
    modelo: Mapped[str | None] = mapped_column(String(60))
    ia_intentos: Mapped[int] = mapped_column(Integer, default=0)
    # primera | regenerar | lesion (PG-20: una lesión nueva regenera el plan sola)
    motivo: Mapped[str] = mapped_column(String(12))
    esquema: Mapped[str] = mapped_column(String(20))  # cuerpo_completo | torso_pierna | division (PG-24)
    objetivo_tipo: Mapped[str] = mapped_column(String(12))  # fuerza | musculo | resistencia (rangos de PG-25)
    explicacion: Mapped[str] = mapped_column(Text)  # PG-27: se guarda junto a la versión
    # PG-20: grupos que no se pudieron entrenar por las lesiones, y otros avisos para el usuario.
    avisos: Mapped[list] = mapped_column(JSON, default=list)
    # Con qué datos se armó (para saber si el perfil o las lesiones cambiaron después).
    parametros: Mapped[dict] = mapped_column(JSON, default=dict)
    duracion_ms: Mapped[int] = mapped_column(Integer, default=0)
    creada_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())

    dias: Mapped[list["RutinaDia"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="RutinaDia.orden", lazy="selectin",
    )


class RutinaDia(Base):
    __tablename__ = "rutina_dia"
    __table_args__ = (UniqueConstraint("rutina_id", "dia_semana"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rutina_id: Mapped[int] = mapped_column(ForeignKey("rutina.id", ondelete="CASCADE"), index=True)
    dia_semana: Mapped[str] = mapped_column(String(10))  # lunes … domingo
    orden: Mapped[int] = mapped_column(Integer)  # 0 = lunes … 6 = domingo
    enfoque: Mapped[str] = mapped_column(String(60))  # ej. "Torso", "Pierna", "Cuerpo completo A"
    grupos: Mapped[list] = mapped_column(JSON, default=list)  # grupos musculares principales del día
    explicacion: Mapped[str] = mapped_column(Text, default="")  # PG-27: máximo 3 líneas

    ejercicios: Mapped[list["RutinaEjercicio"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="RutinaEjercicio.orden", lazy="selectin",
    )


class RutinaEjercicio(Base):
    """El ejercicio "abstracto" del plan: no depende del gym (la adaptación del día lo resuelve)."""

    __tablename__ = "rutina_ejercicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    rutina_dia_id: Mapped[int] = mapped_column(ForeignKey("rutina_dia.id", ondelete="CASCADE"), index=True)
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicio.id", ondelete="RESTRICT"))
    orden: Mapped[int] = mapped_column(Integer)
    series: Mapped[int] = mapped_column(Integer)
    reps_min: Mapped[int] = mapped_column(Integer)
    reps_max: Mapped[int] = mapped_column(Integer)
    descanso_seg: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(200), default="")  # PG-27: una frase
    precaucion: Mapped[bool] = mapped_column(Boolean, default=False)  # lesión en reintroducción (PG-20)

    ejercicio: Mapped["Ejercicio"] = relationship(lazy="joined")


class AdaptacionDia(Base):
    """PG-28: la sesión de hoy adaptada a un gym. Se guarda para no volver a llamar a la IA si nada cambió
    (mismo día del plan, mismo gym, mismo inventario y mismas lesiones). La sesión en vivo (Sprint 4) parte de aquí."""

    __tablename__ = "adaptacion_dia"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    gym_id: Mapped[int | None] = mapped_column(ForeignKey("gym.id", ondelete="CASCADE"), index=True)
    rutina_dia_id: Mapped[int] = mapped_column(ForeignKey("rutina_dia.id", ondelete="CASCADE"))
    fecha: Mapped[date] = mapped_column(Date)
    firma: Mapped[str] = mapped_column(String(64))  # resumen de inventario + lesiones con que se adaptó
    origen: Mapped[str] = mapped_column(String(10))  # ia | reglas
    resultado: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())


from app.models.catalogo import Ejercicio  # noqa: E402  (al final para evitar importación circular)
