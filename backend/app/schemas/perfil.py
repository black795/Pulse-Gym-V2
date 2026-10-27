from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Sexo = Literal["masculino", "femenino", "otro"]
Objetivo = Literal["bajar_grasa", "ganar_musculo", "fuerza", "resistencia", "salud_general"]
Nivel = Literal["principiante", "intermedio", "avanzado"]


class PerfilIn(BaseModel):
    """Todo es opcional: cada pantalla del registro envía solo lo suyo. Los rangos vienen de la tarjeta PG-02."""

    model_config = ConfigDict(extra="forbid")
    edad: int | None = Field(default=None, ge=16, le=90)
    sexo: Sexo | None = None
    peso_kg: float | None = Field(default=None, ge=30, le=250)  # dato sensible
    altura_cm: float | None = Field(default=None, ge=120, le=230)  # dato sensible
    grasa_pct: float | None = Field(default=None, ge=3, le=60)  # dato sensible
    masa_muscular_kg: float | None = Field(default=None, ge=10, le=150)  # dato sensible
    objetivo: Objetivo | None = None
    nivel: Nivel | None = None
    dias_por_semana: int | None = Field(default=None, ge=1, le=7)
    minutos_por_sesion: int | None = Field(default=None, ge=20, le=180)
    descanso_default_seg: int | None = Field(default=None, ge=15, le=600)


class MedicionOut(BaseModel):
    fecha: date
    peso_kg: float | None
    grasa_pct: float | None
    masa_muscular_kg: float | None


class ConsentimientoEstadoOut(BaseModel):
    estado: Literal["pendiente", "aceptado", "rechazado"]
    version_aceptada: str | None
    aceptado_at: datetime | None
    version_vigente: str


class PerfilOut(BaseModel):
    nombre: str
    email: str
    edad: int | None
    sexo: str | None
    altura_cm: float | None
    descanso_default_seg: int
    objetivo: str | None
    nivel: str | None
    dias_por_semana: int | None
    minutos_por_sesion: int | None
    ultima_medicion: MedicionOut | None
    imc: float | None
    imc_categoria: str | None
    faltan: list[str]  # campos obligatorios que aún faltan para generar el plan
    puede_generar_plan: bool
    plan_requiere_regenerar: bool
    consentimiento: ConsentimientoEstadoOut


class ConsentimientoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acepta: bool


class SeccionConsentimiento(BaseModel):
    titulo: str
    texto: str


class TextoConsentimientoOut(BaseModel):
    version: str
    titulo: str
    secciones: list[SeccionConsentimiento]
