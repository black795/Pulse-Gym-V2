from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ahora


class Usuario(Base):
    """Un solo rol: usuario. No existe campo de rol (decisión del 22/10/2026)."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # nunca la contraseña real
    # Sube de 1 cada vez que se cambia la contraseña: las sesiones anteriores dejan de servir.
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Perfil básico (PG-02). altura_cm es dato sensible: solo se guarda si hay consentimiento.
    edad: Mapped[int | None] = mapped_column(Integer)
    sexo: Mapped[str | None] = mapped_column(String(20))
    altura_cm: Mapped[float | None] = mapped_column(Float)
    descanso_default_seg: Mapped[int] = mapped_column(Integer, default=90, server_default="90")

    # Consentimiento de datos sensibles (PG-05): pendiente | aceptado | rechazado
    consentimiento_estado: Mapped[str] = mapped_column(String(20), default="pendiente", server_default="pendiente")
    consentimiento_version: Mapped[str | None] = mapped_column(String(30))
    consentimiento_at: Mapped[datetime | None] = mapped_column(DateTime)

    # PG-19 → PG-20: cuando cambia una lesión, el plan debe regenerarse (lo consume el Sprint 3).
    plan_requiere_regenerar: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora, server_default=func.now())

    objetivo: Mapped["UsuarioObjetivo | None"] = relationship(
        back_populates="usuario", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )
    mediciones: Mapped[list["Medicion"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Medicion.fecha.desc(), Medicion.id.desc()",
    )
    lesiones: Mapped[list["Lesion"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Lesion.created_at.desc()",
    )

    @property
    def consentimiento_aceptado(self) -> bool:
        return self.consentimiento_estado == "aceptado"


class UsuarioObjetivo(Base):
    """Qué busca el usuario y cuánto tiempo tiene. Con esto la IA arma el plan (Sprint 3)."""

    __tablename__ = "usuario_objetivo"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), unique=True)
    objetivo: Mapped[str | None] = mapped_column(String(30))
    nivel: Mapped[str | None] = mapped_column(String(20))
    dias_por_semana: Mapped[int | None] = mapped_column(Integer)
    minutos_por_sesion: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora, server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="objetivo")


class Medicion(Base):
    """Peso y composición corporal en una fecha. Dato sensible. La primera alimenta PG-45 (historial)."""

    __tablename__ = "medicion"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    fecha: Mapped[date] = mapped_column(Date, default=lambda: ahora().date())
    peso_kg: Mapped[float | None] = mapped_column(Float)
    grasa_pct: Mapped[float | None] = mapped_column(Float)
    masa_muscular_kg: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="mediciones")


class Lesion(Base):
    """Lesión o molestia del usuario (PG-19). Dato sensible."""

    __tablename__ = "lesion"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    zona_id: Mapped[int] = mapped_column(ForeignKey("zona_lesion.id", ondelete="RESTRICT"))
    tipo: Mapped[str] = mapped_column(String(10))  # aguda | cronica
    duele_con_carga: Mapped[bool] = mapped_column(Boolean, default=False)
    descripcion: Mapped[str | None] = mapped_column(String(300))
    estado: Mapped[str] = mapped_column(String(20), default="activa")  # activa | reintroduccion | recuperada
    recuperada_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, onupdate=ahora, server_default=func.now())

    usuario: Mapped[Usuario] = relationship(back_populates="lesiones")
    zona: Mapped["ZonaLesion"] = relationship(lazy="joined")


from app.models.catalogo import ZonaLesion  # noqa: E402  (al final para evitar importación circular)
