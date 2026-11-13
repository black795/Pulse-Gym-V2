"""Progresión de pesos (Sprint 5): peso inicial, sobrecarga progresiva (PG-41), retorno tras una ausencia (PG-42) y
estancamiento (PG-43).

Funciones puras: no tocan la base de datos (pesos_service.py les pasa los datos ya leídos), así se prueban solas.

Reglas PROPUESTAS (igual que los rangos de PG-25, las debe validar un entrenador antes del lanzamiento):
- Doble progresión: si la vez pasada hiciste todas las series del plan con tu peso más alto llegando al tope del
  rango de repeticiones, hoy subes un escalón; si no, mantienes el peso e intentas una repetición más.
- Si con ese peso no llegaste ni al mínimo del rango en ninguna serie, bajas un escalón.
- Escalón: 2,5 kg en ejercicios que mueven varias articulaciones y 1 kg en los de una, nunca más del 10 % del peso
  (con pesos chicos, 0,5 kg). Todo se redondea de medio en medio kilo, como los discos.
- Si pasaron 14 días o más desde la última vez, bajas 10 % para cuidar las articulaciones (PG-42).
- Con una lesión en recuperación (ejercicio marcado con precaución) el peso nunca sube.
- La primera vez: un peso inicial prudente, estimado por la IA dentro de un margen de las reglas, o por las reglas.
"""
import math
from dataclasses import dataclass
from datetime import date
from itertools import takewhile

PESO_MAX = 500.0  # el mismo límite que acepta el registro de series (PG-35)
DIAS_RETORNO = 14
REDUCCION_RETORNO = 0.10
SESIONES_ESTANCAMIENTO = 3
DIAS_ESTANCAMIENTO = 14
MARGEN_IA = (0.5, 1.5)  # el peso de la IA se acepta entre la mitad y 1,5 veces la estimación de reglas

# Peso inicial por reglas: fracción del peso corporal según el tipo de ejercicio (para un principiante).
GRUPOS_PIERNA = {"cuadriceps", "isquiotibiales", "gluteos"}
FRACCION_CORPORAL = {
    ("maquina", True, True): 0.6,  # prensa, sentadilla hack…
    ("maquina", True, False): 0.35,  # press de pecho, jalón, remo…
    ("maquina", False, None): 0.2,  # extensión de piernas, curl en máquina…
    ("peso_libre", True, None): 0.3,  # barra o mancuerna en básicos
    ("peso_libre", False, None): 0.08,  # mancuerna en ejercicios de una articulación (cada una)
}
FACTOR_NIVEL = {"principiante": 1.0, "intermedio": 1.3, "avanzado": 1.6}
FACTOR_SEXO = {"masculino": 1.0, "femenino": 0.7}  # "otro" o sin dato: un punto medio
FACTOR_SEXO_DEFECTO = 0.85
PESO_CORPORAL_DEFECTO = {"masculino": 75.0, "femenino": 60.0}
PESO_CORPORAL_SIN_DATO = 70.0
FACTOR_PRECAUCION = 0.7
FACTOR_MAYOR = 0.8  # 60 años o más
MINIMO_KG = {"maquina": 5.0, "peso_libre": 2.0}


@dataclass(frozen=True)
class SesionPasada:
    """Lo que hiciste en un ejercicio en una sesión anterior."""
    fecha: date
    series: list[tuple[float, int]]  # (peso, repeticiones) en el orden en que se hicieron
    series_plan: int
    reps_min: int
    reps_max: int


@dataclass(frozen=True)
class PerfilFisico:
    nivel: str | None = None
    sexo: str | None = None
    edad: int | None = None
    peso_kg: float | None = None


@dataclass(frozen=True)
class EjercicioDatos:
    categoria: str  # maquina | peso_libre | sin_equipo
    multiarticular: bool
    grupo: str | None = None  # músculo principal
    precaucion: bool = False


@dataclass(frozen=True)
class Sugerencia:
    peso_kg: float
    reps: int
    tipo: str  # subir | mantener | bajar | retorno | inicial
    texto: str


def redondear(kg: float) -> float:
    """De medio en medio kilo, entre 0 y 500."""
    return min(PESO_MAX, max(0.0, round(kg * 2) / 2))


def kg(n: float) -> str:
    """72.5 → "72,5 kg"; 40.0 → "40 kg"."""
    return f"{n:g}".replace(".", ",") + " kg"


def incremento(peso: float, multiarticular: bool) -> float:
    base = 2.5 if multiarticular else 1.0
    return max(0.5, min(base, redondear(peso * 0.1)))


def peso_inicial_reglas(e: EjercicioDatos, p: PerfilFisico) -> float:
    """Un peso de partida prudente para alguien que hace el ejercicio por primera vez. Sin equipo: 0 (su cuerpo)."""
    if e.categoria not in MINIMO_KG:
        return 0.0
    pierna = e.grupo in GRUPOS_PIERNA if e.categoria == "maquina" and e.multiarticular else None
    fraccion = FRACCION_CORPORAL[(e.categoria, e.multiarticular, pierna)]
    corporal = p.peso_kg or PESO_CORPORAL_DEFECTO.get(p.sexo or "", PESO_CORPORAL_SIN_DATO)
    factor = FACTOR_NIVEL.get(p.nivel or "", 1.0) * FACTOR_SEXO.get(p.sexo or "", FACTOR_SEXO_DEFECTO)
    if p.edad is not None and p.edad >= 60:
        factor *= FACTOR_MAYOR
    if e.precaucion:
        factor *= FACTOR_PRECAUCION
    return redondear(max(MINIMO_KG[e.categoria], corporal * fraccion * factor))


def validar_peso_ia(valor: float | None, referencia: float) -> float | None:
    """La IA propone, las reglas acotan: se acepta su peso solo dentro del margen de la estimación de reglas.
    None si la IA no mandó un número utilizable (se usa el de reglas)."""
    if valor is None or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return None
    if referencia <= 0:
        return 0.0
    bajo, alto = MARGEN_IA
    return redondear(min(max(float(valor), referencia * bajo), referencia * alto))


def _top(s: SesionPasada) -> tuple[float, list[int]]:
    """Tu peso más alto de esa vez y las repeticiones de cada serie con ese peso."""
    top = max(p for p, _ in s.series)
    return top, [r for p, r in s.series if p == top]


def _marca(top: float, reps: list[int]) -> str:
    repeticiones = ", ".join(str(r) for r in reps)
    return f"{kg(top)} × {repeticiones}" if top > 0 else f"{repeticiones} repeticiones sin peso"


def sugerir(historial: list[SesionPasada], hoy: date, reps_min: int, reps_max: int, multiarticular: bool,
            precaucion: bool = False) -> Sugerencia | None:
    """PG-41/PG-42: el peso para hoy según tu historial (más reciente primero). None si nunca lo hiciste."""
    veces = [s for s in historial if s.series]
    if not veces:
        return None
    ultima = veces[0]
    top, en_top = _top(ultima)
    dias = (hoy - ultima.fecha).days

    if dias >= DIAS_RETORNO:
        peso = redondear(top * (1 - REDUCCION_RETORNO))
        semanas = dias // 7
        return Sugerencia(peso, reps_min, "retorno",
                          f"Volviste después de {semanas} semanas: bajamos un 10 % ({kg(top)} → {kg(peso)}) "
                          "para cuidar tus articulaciones." if top > 0 else
                          f"Volviste después de {semanas} semanas: empieza suave y ve subiendo.")
    if top <= 0:
        reps = min(100, max(en_top) + 1)
        return Sugerencia(0.0, reps, "mantener", f"La vez pasada: {_marca(top, en_top)}. Hoy intenta {reps}.")

    logro = sum(1 for r in en_top if r >= ultima.reps_max) >= ultima.series_plan
    if logro and precaucion:
        return Sugerencia(top, reps_max, "mantener",
                          f"Completaste {ultima.series_plan}×{ultima.reps_max} con {kg(top)}, pero estás cuidando una "
                          "lesión: mantén el peso hasta recuperarte.")
    if logro:
        peso = redondear(top + incremento(top, multiarticular))
        return Sugerencia(peso, reps_min, "subir",
                          f"Completaste {ultima.series_plan}×{ultima.reps_max} con {kg(top)} la última vez → "
                          f"hoy intenta {kg(peso)}.")
    if max(en_top) < ultima.reps_min:
        peso = redondear(top - incremento(top, multiarticular))
        return Sugerencia(peso, reps_min, "bajar",
                          f"La vez pasada no llegaste a {ultima.reps_min} repeticiones con {kg(top)}: "
                          f"hoy prueba con {kg(peso)}.")
    reps = min(reps_max, max(reps_min, min(en_top) + 1))
    return Sugerencia(top, reps, "mantener",
                      f"La vez pasada: {_marca(top, en_top)}. Mantén {kg(top)} e intenta {reps} repeticiones "
                      "en cada serie.")


def sugerencia_inicial(peso: float, reps_max: int, origen: str) -> Sugerencia:
    """La primera vez: el peso estimado (por la IA, acotado por las reglas, o solo por las reglas)."""
    quien = "la IA" if origen == "ia" else "tu perfil"
    return Sugerencia(peso, reps_max, "inicial",
                      f"Primera vez: empieza con {kg(peso)} (estimado según {quien}). Si te sobran repeticiones, "
                      "la próxima vez subimos.")


def estancamiento(historial: list[SesionPasada], hoy: date) -> tuple[float, int, int] | None:
    """PG-43: (peso, sesiones, días) si llevas varias sesiones seguidas con el mismo peso más alto sin hacer más
    repeticiones. Solo si entrenaste ese ejercicio hace poco (si volviste de una ausencia, aplica PG-42)."""
    veces = [s for s in historial if s.series]
    if len(veces) < SESIONES_ESTANCAMIENTO or (hoy - veces[0].fecha).days >= DIAS_RETORNO:
        return None
    peso, reps_reciente = _top(veces[0])
    if peso <= 0:
        return None
    racha = list(takewhile(lambda s: _top(s)[0] == peso, veces))
    if len(racha) < SESIONES_ESTANCAMIENTO:
        return None
    dias = (racha[0].fecha - racha[-1].fecha).days
    if dias < DIAS_ESTANCAMIENTO or max(reps_reciente) > max(_top(racha[-1])[1]):
        return None  # todavía no son 2 semanas, o sí mejoraste las repeticiones con ese peso
    return peso, len(racha), dias
