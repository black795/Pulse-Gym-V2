from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.plan import DiaSemana, EjercicioBreveOut, PesoSugeridoOut


class ConstanciaOut(BaseModel):
    """PG-38: constancia del usuario. Solo cuentan las sesiones completas (PG-37)."""
    racha_actual: int
    mejor_racha: int
    entreno_hoy: bool
    sesiones_semana: int  # lunes a domingo de la semana de `fecha`
    sesiones_mes: int  # mes calendario de `fecha`
    ultima_sesion: date | None


class SesionHistorialOut(BaseModel):
    """PG-46: una fila del historial (resumen, sin el detalle de series)."""
    id: int
    fecha: date
    dia: DiaSemana
    enfoque: str
    gym_nombre: str | None
    estado: str
    cuenta_asistencia: bool
    duracion_seg: int
    series_hechas: int
    series_planeadas: int
    volumen_kg: float
    records: int


class HistorialOut(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    sesiones: list[SesionHistorialOut]


# ---------------- Sprint 5: historial de máquinas y pesos (solo ejercicios que ya hiciste) ----------------
class MarcaOut(BaseModel):
    peso_kg: float
    repeticiones: int


class EjercicioUsadoOut(BaseModel):
    """Un ejercicio (con su máquina, si usa una) que ya hiciste al menos una vez."""
    ejercicio: EjercicioBreveOut
    veces: int  # sesiones en que lo hiciste
    primera_fecha: date
    ultima_fecha: date
    ultima: list[MarcaOut]  # las series de la última vez
    peso_inicial_kg: float  # tu peso más alto la primera vez
    peso_actual_kg: float  # tu peso más alto la última vez
    mejor: MarcaOut  # PG-40: tu récord (más peso; a igual peso, más repeticiones)
    sugerencia: PesoSugeridoOut | None  # PG-41: el peso para la próxima vez


class EjerciciosUsadosOut(BaseModel):
    ejercicios: list[EjercicioUsadoOut]  # el más reciente primero


class SerieHistorialOut(BaseModel):
    numero: int
    peso_kg: float
    repeticiones: int
    es_record: bool


class VezOut(BaseModel):
    """Una sesión en la que hiciste el ejercicio (un punto del gráfico de evolución)."""
    sesion_id: int
    fecha: date
    gym_nombre: str | None
    peso_max_kg: float
    reps_con_peso_max: int
    volumen_kg: float
    record: bool
    series: list[SerieHistorialOut]


class AlertaOut(BaseModel):
    """PG-42 (volviste después de una ausencia) y PG-43 (estancamiento)."""
    tipo: Literal["retorno", "estancamiento"]
    titulo: str
    texto: str
    ejercicio_id: int | None = None


class EjercicioDetalleOut(EjercicioUsadoOut):
    historial: list[VezOut]  # de la más antigua a la más reciente (las últimas 60), para el gráfico
    estancamiento: AlertaOut | None


class AlertasOut(BaseModel):
    alertas: list[AlertaOut]
