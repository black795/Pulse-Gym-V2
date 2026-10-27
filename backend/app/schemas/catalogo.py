from pydantic import BaseModel


class GrupoOut(BaseModel):
    codigo: str
    nombre: str


class MaquinaOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    otros_nombres: list[str]
    tipo: str
    fotos: list[str]
    ejercicios: int
    musculo_principal: str | None = None


class ContraindicacionOut(BaseModel):
    zona: str
    zona_nombre: str
    nivel: str  # evitar | precaucion


class MaquinaResumenOut(BaseModel):
    codigo: str
    nombre: str


class EjercicioResumenOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    musculo_principal: str | None
    dificultad: str
    categoria_equipo: str
    maquinas: list[MaquinaResumenOut]


class EjercicioFichaOut(EjercicioResumenOut):
    musculos_secundarios: list[str]
    multiarticular: bool
    instrucciones: str
    contraindicaciones: list[ContraindicacionOut]
    contraindicaciones_revisadas: bool


class AlternativaOut(EjercicioResumenOut):
    nivel_busqueda: int  # 1 = otra máquina del mismo músculo, 2 = peso libre, 3 = sin equipo
    precaucion: bool  # el usuario tiene una lesión donde este ejercicio pide cuidado
