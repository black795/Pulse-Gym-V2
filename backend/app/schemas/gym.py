from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EstadoMaquina = Literal["disponible", "malograda", "retirada"]


def _texto_limpio(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())  # quita espacios repetidos y en los extremos
    return v or None


class GymIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str = Field(min_length=1, max_length=60)
    ubicacion: str | None = Field(default=None, max_length=120)

    _limpiar = field_validator("nombre", "ubicacion")(_texto_limpio)

    @field_validator("nombre")
    @classmethod
    def _obligatorio(cls, v: str | None) -> str:
        if not v:
            raise ValueError("El nombre del gym es obligatorio.")
        return v


class GymCambioIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    ubicacion: str | None = Field(default=None, max_length=120)

    _limpiar = field_validator("nombre", "ubicacion")(_texto_limpio)


class ImplementosIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    implementos: list[str] = Field(default_factory=list, max_length=30)
    mancuernas_max_kg: float | None = Field(default=None, gt=0, le=150)


class EstadoMaquinaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: EstadoMaquina


class ConfirmarIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str = Field(min_length=2, max_length=40)
    origen: Literal["sugerencia", "manual"]
    # PG-12: si la máquina ya estaba en el gym, true = quedarse con esta foto nueva.
    reemplazar_foto: bool = False


class AgregarMaquinaManualIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str = Field(min_length=2, max_length=40)


class MaquinaOpcionOut(BaseModel):
    """Lo que el usuario necesita para reconocer una máquina: nombre, foto de referencia y músculo principal (PG-09)."""
    codigo: str
    nombre: str
    tipo: str
    foto_ref: str | None
    musculo_principal: str | None


class GymMaquinaOut(BaseModel):
    id: int
    maquina: MaquinaOpcionOut
    estado: EstadoMaquina
    estado_at: datetime
    foto_url: str | None  # enlace temporal (vence en 1 hora)
    agregada_at: datetime
    historial_estados: list[dict]


class ImplementoOut(BaseModel):
    codigo: str
    nombre: str
    marcado: bool


class GymResumenOut(BaseModel):
    id: int
    nombre: str
    ubicacion: str | None
    maquinas: int  # sin contar las retiradas
    implementos: int
    ultimo_uso_at: datetime | None
    es_ultimo_usado: bool
    created_at: datetime


class GymDetalleOut(GymResumenOut):
    inventario: list[GymMaquinaOut]
    lista_implementos: list[ImplementoOut]
    mancuernas_max_kg: float | None


class GymsOut(BaseModel):
    gyms: list[GymResumenOut]
    maximo: int


class FotoOut(BaseModel):
    id: int
    gym_id: int
    estado: str
    url: str
    tomada_at: datetime


class SugerenciaOut(BaseModel):
    puesto: int
    confianza: float
    maquina: MaquinaOpcionOut
    ya_en_inventario: bool


class ReconocimientoOut(BaseModel):
    foto: FotoOut
    es_maquina_de_gym: bool
    confianza_alta: bool  # true → el usuario solo confirma la primera
    umbral_alta: float
    sugerencias: list[SugerenciaOut]
    modelo: str
    duracion_ms: int


class ConfirmarOut(BaseModel):
    accion: Literal["agregada", "foto_actualizada"]
    gym_maquina: GymMaquinaOut
