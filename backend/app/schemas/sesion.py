from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.catalogo import AlternativaOut
from app.schemas.plan import DiaSemana, EjercicioBreveOut, PesoSugeridoOut

MotivoReemplazo = Literal["maquina_ocupada", "molestia_dolor"]
# manual (Sprint 5, PG-39): completada a mano después ("olvidé marcar series") o un entrenamiento pasado.
EstadoTerminada = Literal["completa", "parcial", "manual"]


class IniciarSesionIn(BaseModel):
    """PG-30: se inicia la sesión de hoy (la misma que muestra /api/hoy) y queda congelada."""
    model_config = ConfigDict(extra="forbid")
    gym_id: int | None = None
    dia: DiaSemana | None = Field(default=None, description="Para hacer un día adelantado del plan.")
    fecha: date | None = Field(default=None, description="Fecha local del celular (AAAA-MM-DD).")


class SerieIn(BaseModel):
    """PG-35: lo que hiciste en una serie. Peso 0 = sin peso (ejercicio con tu cuerpo)."""
    model_config = ConfigDict(extra="forbid")
    peso_kg: float = Field(ge=0, le=500)
    repeticiones: int = Field(ge=1, le=100)


class ReemplazoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ejercicio_id: int
    motivo: MotivoReemplazo
    zona: str | None = Field(default=None, description="PG-22: la zona que molesta (obligatoria con molestia_dolor).")
    guardar_lesion: bool = Field(default=False, description="PG-22: guardar la molestia en tu perfil de lesiones.")


class SerieOut(BaseModel):
    numero: int
    peso_kg: float
    repeticiones: int
    es_record: bool
    completada_at: datetime


class SerieAnteriorOut(BaseModel):
    numero: int
    peso_kg: float
    repeticiones: int


class MejorMarcaOut(BaseModel):
    peso_kg: float
    repeticiones: int


class SesionEjercicioOut(BaseModel):
    id: int
    orden: int
    ejercicio: EjercicioBreveOut
    reemplaza: EjercicioBreveOut | None
    motivo: str
    nota: str | None
    precaucion: bool
    series: int
    reps_min: int
    reps_max: int
    descanso_seg: int
    cerrado: bool  # reemplazado en vivo después de algunas series
    hechas: list[SerieOut]
    anterior: list[SerieAnteriorOut]  # PG-35: "vez pasada" (la última sesión con este ejercicio)
    mejor: MejorMarcaOut | None  # PG-40: tu récord antes de esta sesión
    sugerencia: PesoSugeridoOut | None = None  # Sprint 5 (PG-41): el peso para hoy (solo con la sesión en curso)


class RecordOut(BaseModel):
    ejercicio: str
    peso_kg: float
    repeticiones: int


class ResumenOut(BaseModel):
    """PG-37: la calificación al finalizar."""
    estado: EstadoTerminada
    cuenta_asistencia: bool
    duracion_seg: int
    duracion_estimada_seg: int
    series_hechas: int
    series_planeadas: int
    porcentaje: int
    volumen_kg: float
    records: list[RecordOut]
    mensaje: str


class SesionOut(BaseModel):
    id: int
    estado: Literal["en_curso", "completa", "parcial", "manual"]
    fecha: date
    dia: DiaSemana
    enfoque: str
    gym_id: int | None
    gym_nombre: str | None
    inicio_at: datetime
    fin_at: datetime | None
    ahora: datetime  # hora del servidor, para que el cronómetro no dependa del reloj del celular
    duracion_estimada_seg: int
    series_hechas: int
    series_planeadas: int
    volumen_kg: float
    cerrada_auto: bool
    ejercicios: list[SesionEjercicioOut]
    resumen: ResumenOut | None  # solo cuando ya terminó


class OpcionesReemplazoOut(BaseModel):
    """PG-29 / PG-22: reemplazos para hoy (tu plan semanal no cambia)."""
    motivo: MotivoReemplazo
    zona: str | None
    opciones: list[AlternativaOut]  # en orden: otra máquina libre → peso libre → sin equipo
    puede_guardar_lesion: bool  # hay consentimiento de datos de salud
    aviso: str | None


# ---------------- Sprint 5, PG-39: registrar un entrenamiento pasado ----------------
class SeriePasadaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    peso_kg: float = Field(ge=0, le=500)
    repeticiones: int = Field(ge=1, le=100)


class EjercicioPasadoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ejercicio_id: int = Field(description="Uno de los ejercicios de ese día adaptado al gym (los de /api/hoy).")
    series: list[SeriePasadaIn] = Field(default_factory=list, max_length=20)


class SesionPasadaIn(BaseModel):
    """Entrenaste y olvidaste anotarlo: el día del plan que hiciste, dónde, cuándo (hasta 7 días atrás) y las series."""
    model_config = ConfigDict(extra="forbid")
    fecha: date
    dia: DiaSemana
    gym_id: int | None = None
    ejercicios: list[EjercicioPasadoIn] = Field(min_length=1, max_length=12)
