from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TipoLesion = Literal["aguda", "cronica"]
EstadoLesion = Literal["activa", "reintroduccion", "recuperada"]


class LesionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zona: str = Field(min_length=2, max_length=30)  # código de la lista fija (ej. "rodilla")
    tipo: TipoLesion
    duele_con_carga: bool = False
    descripcion: str | None = Field(default=None, max_length=300)
    estado: Literal["activa", "reintroduccion"] = "activa"


class LesionCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zona: str | None = Field(default=None, min_length=2, max_length=30)
    tipo: TipoLesion | None = None
    duele_con_carga: bool | None = None
    descripcion: str | None = Field(default=None, max_length=300)
    estado: EstadoLesion | None = None


class ZonaOut(BaseModel):
    codigo: str
    nombre: str


class LesionOut(BaseModel):
    id: int
    zona: ZonaOut
    tipo: str
    duele_con_carga: bool
    descripcion: str | None
    estado: str
    created_at: datetime
    recuperada_at: datetime | None


class LesionesOut(BaseModel):
    aviso: str
    lesiones: list[LesionOut]
