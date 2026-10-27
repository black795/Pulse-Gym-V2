"""Catálogo base: lo mantiene el equipo con scripts (no hay panel de administración)."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, true, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ahora


class GrupoMuscular(Base):
    __tablename__ = "grupo_muscular"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))


class ZonaLesion(Base):
    """Lista fija de zonas donde puede haber una lesión (PG-19)."""

    __tablename__ = "zona_lesion"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))


class MaquinaCatalogo(Base):
    __tablename__ = "maquina_catalogo"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)  # MAYÚSCULAS, ej. PRENSA_45
    nombre: Mapped[str] = mapped_column(String(100))
    otros_nombres: Mapped[list] = mapped_column(JSON, default=list)  # cómo la llaman en los gyms de Bolivia
    tipo: Mapped[str] = mapped_column(String(20))  # maquina_guiada | polea | peso_libre | estructura | cardio
    # Una máquina desactivada no se ofrece a la IA ni en búsquedas, pero sigue en los inventarios existentes.
    activa: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora, server_default=func.now())

    fotos: Mapped[list["MaquinaFotoRef"]] = relationship(
        cascade="all, delete-orphan", order_by="MaquinaFotoRef.orden", lazy="selectin"
    )


class MaquinaFotoRef(Base):
    """Fotos de referencia: con ellas la IA compara lo que el usuario fotografía (Sprint 2)."""

    __tablename__ = "maquina_foto_ref"

    id: Mapped[int] = mapped_column(primary_key=True)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquina_catalogo.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500))
    orden: Mapped[int] = mapped_column(Integer, default=0)


class Ejercicio(Base):
    __tablename__ = "ejercicio"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    dificultad: Mapped[str] = mapped_column(String(10))  # facil | media | dificil
    multiarticular: Mapped[bool] = mapped_column(Boolean, default=False)
    # maquina | peso_libre | sin_equipo  (calistenia incluida en sin_equipo)
    categoria_equipo: Mapped[str] = mapped_column(String(15))
    instrucciones: Mapped[str] = mapped_column(Text)
    # Un entrenador debe revisar las contraindicaciones antes de usarlas con usuarios reales.
    contraindicaciones_revisadas: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    activo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    musculos: Mapped[list["EjercicioMusculo"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    maquinas: Mapped[list["EjercicioMaquina"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    contraindicaciones: Mapped[list["EjercicioContraindicacion"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def musculo_principal(self) -> "GrupoMuscular | None":
        return next((m.grupo for m in self.musculos if m.rol == "principal"), None)


class EjercicioMusculo(Base):
    __tablename__ = "ejercicio_musculo"
    __table_args__ = (UniqueConstraint("ejercicio_id", "grupo_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicio.id", ondelete="CASCADE"), index=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo_muscular.id", ondelete="RESTRICT"))
    rol: Mapped[str] = mapped_column(String(10))  # principal | secundario

    grupo: Mapped[GrupoMuscular] = relationship(lazy="joined")


class EjercicioMaquina(Base):
    """Un ejercicio puede hacerse en varias máquinas (y una máquina sirve para varios ejercicios)."""

    __tablename__ = "ejercicio_maquina"
    __table_args__ = (UniqueConstraint("ejercicio_id", "maquina_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicio.id", ondelete="CASCADE"), index=True)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquina_catalogo.id", ondelete="CASCADE"), index=True)

    maquina: Mapped[MaquinaCatalogo] = relationship(lazy="joined")


class EjercicioContraindicacion(Base):
    __tablename__ = "ejercicio_contraindicacion"
    __table_args__ = (UniqueConstraint("ejercicio_id", "zona_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ejercicio_id: Mapped[int] = mapped_column(ForeignKey("ejercicio.id", ondelete="CASCADE"), index=True)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zona_lesion.id", ondelete="RESTRICT"))
    nivel: Mapped[str] = mapped_column(String(10))  # evitar | precaucion

    zona: Mapped[ZonaLesion] = relationship(lazy="joined")


class MaquinaPropuesta(Base):
    """Máquina que el usuario fotografió y la IA encontró en internet (Sprint 2). No entra al catálogo
    oficial hasta que el equipo la revise. La tabla ya existe para que el equipo pueda consultarla (PG-18)."""

    __tablename__ = "maquina_propuesta"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_encontrado: Mapped[str] = mapped_column(String(150))
    foto_url: Mapped[str | None] = mapped_column(String(500))
    fuente_url: Mapped[str | None] = mapped_column(String(500))
    estado: Mapped[str] = mapped_column(String(15), default="pendiente")  # pendiente | aprobada | rechazada
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())
