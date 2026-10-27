"""Mis gyms e IA de fotos (Sprint 2): gym, foto_maquina, reconocimiento_ia y gym_maquina (inventario)."""
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, ahora


class Gym(Base):
    """Un lugar donde el usuario entrena (su gym, otro gym, su casa). PG-06."""

    __tablename__ = "gym"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(60))
    ubicacion: Mapped[str | None] = mapped_column(String(120))
    # PG-14: implementos marcados de una lista fija (códigos de gym_service.IMPLEMENTOS), sin fotografiarlos.
    implementos: Mapped[list] = mapped_column(JSON, default=list)
    mancuernas_max_kg: Mapped[float | None] = mapped_column(Float)
    # PG-06: se recuerda el último gym usado.
    ultimo_uso_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())

    maquinas: Mapped[list["GymMaquina"]] = relationship(
        back_populates="gym", cascade="all, delete-orphan", passive_deletes=True, order_by="GymMaquina.agregada_at",
    )
    fotos: Mapped[list["FotoMaquina"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)


class FotoMaquina(Base):
    """Foto que el usuario tomó en su gym. Privada: el archivo vive fuera de las carpetas públicas (PG-48)."""

    __tablename__ = "foto_maquina"

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gym.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    archivo: Mapped[str] = mapped_column(String(200))  # ruta relativa dentro de FOTOS_DIR
    # pendiente | reconocida_alta | opciones_sugeridas | no_es_maquina | error_ia | busqueda_web | confirmada
    estado: Mapped[str] = mapped_column(String(20), default="pendiente")
    es_maquina_de_gym: Mapped[bool | None] = mapped_column()
    ia_intentos: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    ia_ultimo_error: Mapped[str | None] = mapped_column(String(300))
    ia_duracion_ms: Mapped[int | None] = mapped_column(Integer)

    # PG-09: qué eligió el usuario, para calibrar los umbrales de confianza.
    eleccion: Mapped[str | None] = mapped_column(String(12))  # sugerencia | manual | ninguna
    elegida_maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquina_catalogo.id", ondelete="SET NULL"))
    elegida_puesto: Mapped[int | None] = mapped_column(Integer)  # 1 = primera sugerencia de la IA
    elegida_at: Mapped[datetime | None] = mapped_column(DateTime)

    tomada_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())

    reconocimientos: Mapped[list["ReconocimientoIA"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="[ReconocimientoIA.intento, ReconocimientoIA.puesto]",
    )


class ReconocimientoIA(Base):
    """Cada sugerencia de cada intento de la IA (PG-08): modelo, máquina sugerida, confianza y puesto."""

    __tablename__ = "reconocimiento_ia"

    id: Mapped[int] = mapped_column(primary_key=True)
    foto_id: Mapped[int] = mapped_column(ForeignKey("foto_maquina.id", ondelete="CASCADE"), index=True)
    intento: Mapped[int] = mapped_column(Integer)
    maquina_id: Mapped[int] = mapped_column(ForeignKey("maquina_catalogo.id", ondelete="CASCADE"))
    confianza: Mapped[float] = mapped_column(Float)
    puesto: Mapped[int] = mapped_column(Integer)
    modelo: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())

    maquina: Mapped["MaquinaCatalogo"] = relationship(lazy="joined")


class GymMaquina(Base):
    """Inventario: qué máquinas hay en cada gym. Una sola fila por máquina (PG-12), aunque haya varias unidades."""

    __tablename__ = "gym_maquina"
    __table_args__ = (
        UniqueConstraint("gym_id", "maquina_id", name="uq_gym_maquina"),
        # Apunta al catálogo o a una máquina propuesta (PG-10, Sprint 5), nunca a las dos.
        CheckConstraint(
            "(maquina_id IS NOT NULL AND maquina_propuesta_id IS NULL) OR "
            "(maquina_id IS NULL AND maquina_propuesta_id IS NOT NULL)",
            name="chk_origen_maquina",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    gym_id: Mapped[int] = mapped_column(ForeignKey("gym.id", ondelete="CASCADE"), index=True)
    maquina_id: Mapped[int | None] = mapped_column(ForeignKey("maquina_catalogo.id", ondelete="RESTRICT"))
    maquina_propuesta_id: Mapped[int | None] = mapped_column(ForeignKey("maquina_propuesta.id", ondelete="SET NULL"))
    foto_id: Mapped[int | None] = mapped_column(ForeignKey("foto_maquina.id", ondelete="SET NULL"))
    # PG-13: disponible | malograda (temporal) | retirada
    estado: Mapped[str] = mapped_column(String(12), default="disponible")
    estado_at: Mapped[datetime] = mapped_column(DateTime, default=ahora)
    # PG-13: fecha de cada cambio de estado, [{"estado": ..., "fecha": ISO}]
    historial_estados: Mapped[list] = mapped_column(JSON, default=list)
    agregada_at: Mapped[datetime] = mapped_column(DateTime, default=ahora, server_default=func.now())

    gym: Mapped[Gym] = relationship(back_populates="maquinas")
    maquina: Mapped["MaquinaCatalogo | None"] = relationship(lazy="joined")
    foto: Mapped["FotoMaquina | None"] = relationship(lazy="joined")


from app.models.catalogo import MaquinaCatalogo  # noqa: E402  (al final para evitar importación circular)
