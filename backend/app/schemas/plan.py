from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DiaSemana = Literal["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


class GenerarPlanIn(BaseModel):
    """PG-23: el usuario elige qué días entrena. Si no los manda, se usan los del plan actual (o unos sugeridos)."""
    model_config = ConfigDict(extra="forbid")
    dias: list[DiaSemana] | None = Field(default=None, min_length=1, max_length=7)

    @field_validator("dias")
    @classmethod
    def _sin_repetidos(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(set(v)) != len(v):
            raise ValueError("No repitas días.")
        return v


class EjercicioBreveOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    musculo_principal: str | None  # nombre para mostrar (ej. "Cuádriceps")
    categoria_equipo: str
    maquinas: list[str]  # nombres de las máquinas con que se hace


class RutinaEjercicioOut(BaseModel):
    id: int
    orden: int
    ejercicio: EjercicioBreveOut
    series: int
    reps_min: int
    reps_max: int
    descanso_seg: int
    motivo: str
    precaucion: bool


class RutinaDiaOut(BaseModel):
    id: int
    dia: DiaSemana
    dia_nombre: str
    enfoque: str
    grupos: list[str]  # nombres
    explicacion: str
    minutos_estimados: int
    ejercicios: list[RutinaEjercicioOut]


class LesionEscudoOut(BaseModel):
    zona: str
    nombre: str
    estado: Literal["activa", "reintroduccion"]


class PlanOut(BaseModel):
    id: int
    version: int
    origen: Literal["ia", "mixto", "reglas"]
    modelo: str | None
    motivo: str
    esquema: str
    esquema_texto: str
    objetivo_tipo: str
    explicacion: str
    avisos: list[str]
    lesiones: list[LesionEscudoOut]  # PG-20: "escudo de lesión activo"
    ejercicios_excluidos: int  # cuántos ejercicios del catálogo se quitaron por las lesiones
    creada_at: datetime
    duracion_ms: int
    dias: list[RutinaDiaOut]


class PlanEstadoOut(BaseModel):
    plan: PlanOut | None
    puede_generar: bool
    faltan: list[str]  # datos del perfil que faltan para armar el plan
    dias_sugeridos: list[DiaSemana]
    regeneraciones_restantes: int
    regeneraciones_max: int
    perfil_cambio: bool  # cambiaste objetivo, nivel, minutos o días después de armar el plan


# ---------------- PG-28: hoy ----------------
class GymOpcionOut(BaseModel):
    id: int
    nombre: str
    es_ultimo_usado: bool
    maquinas: int


class EjercicioHoyOut(BaseModel):
    orden: int
    ejercicio: EjercicioBreveOut
    original: EjercicioBreveOut | None  # el del plan, si se cambió
    cambio: bool
    motivo_cambio: str | None  # por qué no se pudo hacer el del plan
    por_que_reemplazo: str | None  # por qué se eligió este
    precaucion: bool
    series: int
    reps_min: int
    reps_max: int
    descanso_seg: int


class OmitidoOut(BaseModel):
    nombre: str
    motivo: str


class SesionHoyOut(BaseModel):
    dia: DiaSemana
    dia_nombre: str
    enfoque: str
    gym_id: int | None
    gym_nombre: str | None
    origen: Literal["ia", "reglas"]
    modelo: str | None
    ejercicios: list[EjercicioHoyOut]
    cambios: int
    omitidos: list[OmitidoOut]
    avisos: list[str]
    sugerir_fotos: bool  # el gym no tiene máquinas registradas
    minutos_estimados: int
    duracion_ms: int


class SiguienteDiaOut(BaseModel):
    dia: DiaSemana
    dia_nombre: str
    enfoque: str


class HoyOut(BaseModel):
    fecha: date
    dia: DiaSemana
    dia_nombre: str
    plan_existe: bool
    es_dia_de_entreno: bool
    siguiente_dia: SiguienteDiaOut | None  # si hoy no toca, para ofrecer adelantarlo
    gyms: list[GymOpcionOut]  # primero el último usado (preseleccionado)
    requiere_elegir_gym: bool
    sesion: SesionHoyOut | None


# ---------------- PG-49 ----------------
class UsoTipoOut(BaseModel):
    tipo: str
    usadas: int
    limite: int


class UsoIAOut(BaseModel):
    tipos: list[UsoTipoOut]
    costo_hoy_usd: float
