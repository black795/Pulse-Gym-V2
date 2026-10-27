"""Importar todos los modelos aquí hace que SQLAlchemy los conozca al crear las tablas."""
from app.models.catalogo import (
    Ejercicio, EjercicioContraindicacion, EjercicioMaquina, EjercicioMusculo, GrupoMuscular,
    MaquinaCatalogo, MaquinaFotoRef, MaquinaPropuesta, ZonaLesion,
)
from app.models.gym import FotoMaquina, Gym, GymMaquina, ReconocimientoIA
from app.models.ia import LlamadaIA
from app.models.plan import AdaptacionDia, Rutina, RutinaDia, RutinaEjercicio
from app.models.seguridad import IntentoLogin, RecuperacionPassword
from app.models.usuario import Lesion, Medicion, Usuario, UsuarioObjetivo

__all__ = [
    "AdaptacionDia", "Ejercicio", "EjercicioContraindicacion", "EjercicioMaquina", "EjercicioMusculo", "FotoMaquina",
    "GrupoMuscular", "Gym", "GymMaquina", "IntentoLogin", "Lesion", "LlamadaIA", "MaquinaCatalogo", "MaquinaFotoRef",
    "MaquinaPropuesta", "Medicion", "ReconocimientoIA", "RecuperacionPassword", "Rutina", "RutinaDia", "RutinaEjercicio",
    "Usuario", "UsuarioObjetivo", "ZonaLesion",
]
