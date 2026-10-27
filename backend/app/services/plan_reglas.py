"""Reglas del plan semanal: lo que NO se negocia (PG-20, PG-23, PG-24, PG-25, PG-26).

Las reglas fijan los límites (qué días, qué grupos cada día, qué ejercicios están permitidos, series, repeticiones y
descansos). Dentro de esos límites la IA elige, ordena y explica (plan_ia.py). Si la IA falla, este módulo arma el
plan solo (la "versión de solo reglas"). Todo plan, venga de donde venga, pasa por `validar` antes de guardarse.

Este archivo no toca la base de datos: recibe un Contexto ya armado (plan_service.py) y devuelve datos simples.
Los esquemas y rangos son una propuesta inicial: los debe validar un entrenador antes del lanzamiento.
"""
import itertools
import re
import unicodedata
from dataclasses import dataclass, field

from app.models.plan import DIAS_SEMANA

NOMBRES_DIAS = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles", "jueves": "Jueves",
    "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}
# PG-23: "cada grupo muscular grande se trabaja al menos 1 vez por semana".
GRUPOS_GRANDES = ("pecho", "espalda", "hombros", "cuadriceps", "isquiotibiales", "gluteos")
MIN_EJERCICIOS, MAX_EJERCICIOS = 4, 8
CALENTAMIENTO_SEG = 300
SEG_POR_SERIE = 40  # lo que dura hacer una serie (sin contar el descanso)
SEG_CAMBIO_EJERCICIO = 60  # acomodar la máquina, cambiar de peso…

# ---------------- PG-24: esquemas según los días disponibles ----------------
# Cada plantilla de día: (enfoque que ve el usuario, grupos en orden de prioridad). Se usan los primeros N
# grupos, donde N es la cantidad de ejercicios que entra en los minutos del usuario.
PLANTILLAS: dict[str, tuple[str, list[str]]] = {
    "completo_a": ("Cuerpo completo A", ["cuadriceps", "pecho", "espalda", "hombros", "isquiotibiales", "core", "biceps", "triceps"]),
    "completo_b": ("Cuerpo completo B", ["gluteos", "espalda", "pecho", "isquiotibiales", "hombros", "cuadriceps", "triceps", "core"]),
    "completo_c": ("Cuerpo completo C", ["isquiotibiales", "pecho", "espalda", "cuadriceps", "hombros", "gluteos", "biceps", "core"]),
    "torso": ("Torso", ["pecho", "espalda", "hombros", "pecho", "espalda", "triceps", "biceps", "core"]),
    "pierna": ("Pierna", ["cuadriceps", "isquiotibiales", "gluteos", "cuadriceps", "pantorrillas", "gluteos", "isquiotibiales", "pantorrillas"]),
    "empuje": ("Empuje: pecho, hombros y tríceps", ["pecho", "hombros", "pecho", "triceps", "hombros", "triceps", "pecho", "hombros"]),
    "tiron": ("Tirón: espalda, bíceps y abdomen", ["espalda", "espalda", "biceps", "core", "espalda", "biceps", "core", "espalda"]),
    "core": ("Abdomen y core", ["core"] * 8),
}
# Por cantidad de días: esquemas en orden de preferencia. El segundo se usa si con el primero quedaría el mismo
# grupo muscular en dos días seguidos (ej. cuerpo completo el lunes y el martes).
ESQUEMAS: dict[int, list[tuple[str, list[str]]]] = {
    1: [("cuerpo_completo", ["completo_a"])],
    2: [("cuerpo_completo", ["completo_a", "completo_b"]), ("torso_pierna", ["torso", "pierna"])],
    3: [("cuerpo_completo", ["completo_a", "completo_b", "completo_c"]), ("division", ["empuje", "tiron", "pierna"])],
    4: [("torso_pierna", ["torso", "pierna", "torso", "pierna"])],
    5: [("division", ["empuje", "tiron", "pierna", "torso", "pierna"])],
    6: [("division", ["empuje", "tiron", "pierna", "empuje", "tiron", "pierna"])],
    7: [("division", ["empuje", "tiron", "pierna", "empuje", "tiron", "pierna", "core"])],
}
TEXTO_ESQUEMA = {
    "cuerpo_completo": "cuerpo completo (trabajas todo el cuerpo cada día)",
    "torso_pierna": "torso y pierna (un día la parte de arriba, otro la de abajo)",
    "division": "división por grupos (empuje, tirón y pierna en días distintos)",
}
SUGERENCIA_DIAS = {
    1: ["miercoles"], 2: ["lunes", "jueves"], 3: ["lunes", "miercoles", "viernes"], 4: ["lunes", "martes", "jueves", "viernes"],
    5: ["lunes", "martes", "miercoles", "viernes", "sabado"], 6: list(DIAS_SEMANA[:6]), 7: list(DIAS_SEMANA),
}

# ---------------- PG-25: series, repeticiones y descanso (a validar con un entrenador) ----------------
RANGOS = {
    "fuerza": {"series": (3, 5), "reps": (3, 6), "descanso": (120, 180)},
    "musculo": {"series": (3, 4), "reps": (8, 12), "descanso": (60, 90)},
    "resistencia": {"series": (2, 3), "reps": (15, 20), "descanso": (30, 60)},
}
# Bajar grasa y salud general usan los rangos de "músculo": conservar músculo mientras se baja grasa es lo que
# recomiendan la mayoría de guías; el entrenador puede cambiarlo aquí.
OBJETIVO_A_TIPO = {
    "fuerza": "fuerza", "ganar_musculo": "musculo", "bajar_grasa": "musculo", "salud_general": "musculo",
    "resistencia": "resistencia",
}
TEXTO_OBJETIVO = {
    "fuerza": "ganar fuerza", "ganar_musculo": "ganar músculo", "bajar_grasa": "bajar grasa sin perder músculo",
    "salud_general": "mejorar tu salud general", "resistencia": "mejorar tu resistencia",
}
SERIES_MAX_PRINCIPIANTE = 3

# PG-27: palabras técnicas → lenguaje simple (si la IA las usa, se reemplazan).
JERGA = {
    r"\bhipertrofia\b": "crecimiento muscular", r"\bRIR\b": "repeticiones de reserva", r"\bRPE\b": "nivel de esfuerzo",
    r"\bAMRAP\b": "todas las repeticiones que puedas", r"\bsuperseries?\b": "dos ejercicios seguidos",
    r"\bexc[eé]ntric[oa]s?\b": "la bajada", r"\bconc[eé]ntric[oa]s?\b": "la subida",
    r"\bisom[eé]tric[oa]s?\b": "sin moverte", r"\bunilateral(es)?\b": "con un lado a la vez",
    r"\bsobrecarga progresiva\b": "subir el peso poco a poco", r"\bmultiarticular(es)?\b": "que mueve varias articulaciones",
    r"\bmonoarticular(es)?\b": "que mueve una sola articulación", r"\bfallo muscular\b": "hasta no poder más",
}


@dataclass
class EjercicioInfo:
    id: int
    codigo: str
    nombre: str
    grupo: str  # músculo principal
    multiarticular: bool
    dificultad: str
    categoria: str
    precaucion: bool = False  # PG-20: lesión en reintroducción en una zona donde pide cuidado


@dataclass
class Contexto:
    """Todo lo que las reglas (y la IA) necesitan saber para armar el plan."""
    dias: list[str]  # ordenados de lunes a domingo
    objetivo: str
    objetivo_tipo: str
    nivel: str
    minutos: int
    permitidos: dict[str, EjercicioInfo]  # códigos que se pueden usar (posibles y no contraindicados)
    bloqueados: dict[str, str]  # código → motivo (contraindicado, sin equipo). Para explicar los rechazos.
    nombres_grupos: dict[str, str]
    zonas: dict[str, str]  # zona → estado de la lesión que limita (activa | reintroduccion)
    nombres_zonas: dict[str, str]
    grupos_omitidos: dict[str, str] = field(default_factory=dict)  # grupo → por qué no se puede entrenar
    perfil: dict = field(default_factory=dict)  # edad, sexo, % grasa, masa muscular (para la IA)
    con_equipo: bool = True
    # Se calculan con `preparar`:
    esquema: str = ""
    plantilla_por_dia: dict[str, str] = field(default_factory=dict)
    n_ejercicios: int = MIN_EJERCICIOS


@dataclass
class EjercicioPlan:
    codigo: str
    series: int
    reps_min: int
    reps_max: int
    descanso_seg: int
    motivo: str = ""
    precaucion: bool = False


@dataclass
class DiaPlan:
    dia: str
    enfoque: str
    grupos: list[str]
    explicacion: str
    ejercicios: list[EjercicioPlan]


@dataclass
class PlanPropuesto:
    explicacion: str
    dias: list[DiaPlan]
    avisos: list[str] = field(default_factory=list)


# ---------------- Utilidades ----------------
def sin_tildes(t: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(ch) != "Mn")


def ordenar_dias(dias: list[str]) -> list[str]:
    return sorted(set(dias), key=DIAS_SEMANA.index)


def son_seguidos(a: str, b: str) -> bool:
    """Días consecutivos en el calendario. El domingo y el lunes también lo son: la semana se repite."""
    return (DIAS_SEMANA.index(b) - DIAS_SEMANA.index(a)) % 7 in (1, 6)


def grupos_de_plantilla(clave: str) -> set[str]:
    return set(PLANTILLAS[clave][1])


def lista(items: list[str]) -> str:
    """["pecho", "espalda", "hombros"] → "pecho, espalda y hombros"."""
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]


# ---------------- PG-25 ----------------
def prescripcion(tipo: str, nivel: str, multiarticular: bool) -> tuple[int, int, int, int]:
    """(series, reps_min, reps_max, descanso_seg) dentro de los rangos de PG-25. Los básicos pesados (ejercicios
    que mueven varias articulaciones) llevan más descanso; los principiantes, menos volumen."""
    r = RANGOS[tipo]
    smin, smax = r["series"]
    series = {"principiante": smin, "intermedio": smin + 1 if multiarticular else smin,
              "avanzado": smax if multiarticular else max(smin, smax - 1)}.get(nivel, smin)
    if nivel == "principiante":
        series = min(series, SERIES_MAX_PRINCIPIANTE)
    rmin, rmax = r["reps"]
    if tipo == "resistencia":
        reps = (rmin, rmax)
    else:
        medio = (rmin + rmax) // 2
        reps = (rmin, medio) if multiarticular else (medio, rmax)
    descanso = r["descanso"][1] if multiarticular else r["descanso"][0]
    return series, reps[0], reps[1], descanso


def segundos_ejercicio(series: int, descanso: int) -> int:
    return series * (SEG_POR_SERIE + descanso) + SEG_CAMBIO_EJERCICIO


def ejercicios_por_minutos(tipo: str, nivel: str, minutos: int) -> int:
    """PG-23: entre 4 y 8 ejercicios por día, según los minutos por sesión."""
    s1, *_, d1 = prescripcion(tipo, nivel, True)
    s2, *_, d2 = prescripcion(tipo, nivel, False)
    promedio = (segundos_ejercicio(s1, d1) + segundos_ejercicio(s2, d2)) / 2
    n = int((minutos * 60 - CALENTAMIENTO_SEG) // promedio)
    return max(MIN_EJERCICIOS, min(MAX_EJERCICIOS, n))


def minutos_estimados(ejercicios: list[EjercicioPlan]) -> int:
    return round((CALENTAMIENTO_SEG + sum(segundos_ejercicio(e.series, e.descanso_seg) for e in ejercicios)) / 60)


# ---------------- PG-24 ----------------
def asignar_plantillas(dias: list[str]) -> tuple[str, dict[str, str]]:
    """Elige el esquema y qué plantilla va cada día, sin repetir un grupo principal en días seguidos.
    Se comparan TODOS los grupos de cada plantilla (no solo los primeros), así ningún relleno rompe la regla."""
    for esquema, claves in ESQUEMAS[len(dias)]:
        vistas = set()
        for orden in itertools.permutations(claves):  # primero el orden "natural"
            if orden in vistas:
                continue
            vistas.add(orden)
            asignacion = dict(zip(dias, orden))
            if all(
                not (grupos_de_plantilla(asignacion[a]) & grupos_de_plantilla(asignacion[b]))
                for a, b in itertools.combinations(dias, 2) if son_seguidos(a, b)
            ):
                return esquema, asignacion
    raise ValueError("No hay un esquema posible para esos días.")  # no pasa con los esquemas definidos arriba


def preparar(ctx: Contexto) -> Contexto:
    ctx.dias = ordenar_dias(ctx.dias)
    ctx.n_ejercicios = ejercicios_por_minutos(ctx.objetivo_tipo, ctx.nivel, ctx.minutos)
    ctx.esquema, ctx.plantilla_por_dia = asignar_plantillas(ctx.dias)
    return ctx


def candidatos_del_dia(ctx: Contexto, dia: str) -> dict[str, list[EjercicioInfo]]:
    """Grupo → ejercicios permitidos para ese día (solo de los grupos de su plantilla)."""
    grupos = list(dict.fromkeys(PLANTILLAS[ctx.plantilla_por_dia[dia]][1]))
    return {g: sorted((e for e in ctx.permitidos.values() if e.grupo == g), key=lambda e: _puntaje(ctx, e)) for g in grupos}


def _puntaje(ctx: Contexto, e: EjercicioInfo) -> tuple:
    dificultad = {"principiante": {"facil": 0, "media": 1, "dificil": 3}, "intermedio": {"facil": 1, "media": 0, "dificil": 1},
                  "avanzado": {"facil": 2, "media": 0, "dificil": 0}}.get(ctx.nivel, {}).get(e.dificultad, 1)
    equipo = 1 if ctx.con_equipo and e.categoria == "sin_equipo" else 0
    return (e.precaucion, dificultad, equipo, not e.multiarticular, e.codigo)


# ---------------- Versión de solo reglas ----------------
def armar_con_reglas(ctx: Contexto, explicacion_extra: str = "") -> PlanPropuesto:
    usados_semana: dict[str, int] = {}
    dias: list[DiaPlan] = []
    avisos: list[str] = []
    for dia in ctx.dias:
        clave = ctx.plantilla_por_dia[dia]
        enfoque, slots = PLANTILLAS[clave]
        candidatos = candidatos_del_dia(ctx, dia)
        elegidos: list[EjercicioInfo] = []
        # Se recorren los grupos de la plantilla en orden; si faltan ejercicios, se da otra vuelta.
        for g in slots + slots:
            if len(elegidos) >= ctx.n_ejercicios:
                break
            opciones = [e for e in candidatos.get(g, []) if e not in elegidos]
            if not opciones:
                continue
            primero_del_grupo = all(x.grupo != g for x in elegidos)
            puesto = {e.codigo: k for k, e in enumerate(opciones)}  # orden por puntaje (dificultad, equipo…)
            # Variedad: lo que menos se usó en la semana (así los días A y B no son iguales); el primero de cada
            # grupo, un básico (varias articulaciones); después, el mejor puntaje para el nivel y el equipo.
            opciones.sort(key=lambda e: (usados_semana.get(e.codigo, 0), e.precaucion,
                                         (not e.multiarticular) if primero_del_grupo else 0, puesto[e.codigo]))
            elegidos.append(opciones[0])
            usados_semana[opciones[0].codigo] = usados_semana.get(opciones[0].codigo, 0) + 1
        elegidos.sort(key=lambda e: (not e.multiarticular, slots.index(e.grupo)))  # básicos primero
        ejercicios = []
        for e in elegidos:
            series, rmin, rmax, descanso = prescripcion(ctx.objetivo_tipo, ctx.nivel, e.multiarticular)
            ejercicios.append(EjercicioPlan(e.codigo, series, rmin, rmax, descanso, _motivo_reglas(ctx, e), e.precaucion))
        grupos = list(dict.fromkeys(e.grupo for e in elegidos))
        if len(ejercicios) < MIN_EJERCICIOS:
            avisos.append(f"El {NOMBRES_DIAS[dia].lower()} tiene solo {len(ejercicios)} ejercicios: tus lesiones dejan pocas opciones para ese día.")
        dias.append(DiaPlan(dia, enfoque, grupos, _explicacion_dia_reglas(ctx, enfoque, grupos, elegidos), ejercicios))
    return PlanPropuesto(explicacion=_explicacion_reglas(ctx, explicacion_extra), dias=dias, avisos=avisos)


def _motivo_reglas(ctx: Contexto, e: EjercicioInfo) -> str:
    grupo = ctx.nombres_grupos.get(e.grupo, e.grupo).lower()
    if e.precaucion:
        return f"Hazlo suave y detente si duele: cuida la zona que estás recuperando mientras trabajas {grupo}."
    if e.multiarticular:
        return f"Ejercicio básico para {grupo}: mueve varias articulaciones y te da fuerza general."
    return f"Complementa el trabajo de {grupo} de forma más aislada."


def _explicacion_dia_reglas(ctx: Contexto, enfoque: str, grupos: list[str], elegidos: list[EjercicioInfo]) -> str:
    texto = f"Día de {enfoque.lower()}: trabajas {lista([ctx.nombres_grupos.get(g, g).lower() for g in grupos])}."
    if any(e.precaucion for e in elegidos):
        texto += " Los ejercicios marcados con precaución hazlos suave: tu lesión está en recuperación."
    return texto


def _texto_lesiones(ctx: Contexto) -> str:
    if not ctx.zonas:
        return ""
    zonas = lista([ctx.nombres_zonas.get(z, z).lower() for z in ctx.zonas])
    return f"Cuidamos tu {zonas}: quitamos los ejercicios que la pueden empeorar."


def _explicacion_reglas(ctx: Contexto, extra: str) -> str:
    partes = [
        f"Armamos tus {len(ctx.dias)} días con un esquema de {TEXTO_ESQUEMA[ctx.esquema]}.",
        f"Las series, repeticiones y descansos están pensados para {TEXTO_OBJETIVO.get(ctx.objetivo, ctx.objetivo)}.",
        _texto_lesiones(ctx), extra,
    ]
    return " ".join(p for p in partes if p)


# ---------------- PG-26: validación ----------------
@dataclass
class Revision:
    plan: PlanPropuesto | None
    errores: list[str]  # graves: el plan se rechaza
    correcciones: list[str]  # leves: se corrigieron solas

    @property
    def ok(self) -> bool:
        return self.plan is not None and not self.errores


def _una_frase(t: str, maximo: int = 160) -> str:
    t = " ".join((t or "").split())
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    t = m.group(1) if m else t
    return t if len(t) <= maximo else t[: maximo - 1].rstrip() + "…"


def _max_lineas(t: str, lineas: int = 3, maximo: int = 320) -> str:
    frases = re.findall(r"[^.!?\n]+[.!?]?", " ".join((t or "").split()))
    t = " ".join(f.strip() for f in frases[:lineas] if f.strip())
    return t if len(t) <= maximo else t[: maximo - 1].rstrip() + "…"


def lenguaje_simple(t: str) -> str:
    for patron, simple in JERGA.items():
        t = re.sub(patron, simple, t, flags=re.IGNORECASE)
    return t


def revisar_dia(d: DiaPlan, ctx: Contexto, errores: list[str], correcciones: list[str], obligatorios: list[str] = ()) -> None:
    """Valida y corrige un día (lo usa `validar` y también cada respuesta de la IA por separado).
    `obligatorios`: grupos grandes que el día debe incluir para que la semana los cubra a todos (PG-23)."""
    r = RANGOS[ctx.objetivo_tipo]
    enfoque, slots = PLANTILLAS[ctx.plantilla_por_dia[d.dia]]
    d.enfoque = enfoque  # el enfoque lo fijan las reglas
    grupos_permitidos = set(slots)
    vistos: set[str] = set()
    limpios: list[EjercicioPlan] = []
    for ej in d.ejercicios:
        info = ctx.permitidos.get(ej.codigo)
        if info is None:
            motivo = ctx.bloqueados.get(ej.codigo, "no existe en el catálogo")
            errores.append(f"{ej.codigo} ({NOMBRES_DIAS[d.dia]}): {motivo}")
            continue
        if info.grupo not in grupos_permitidos:
            errores.append(f"{ej.codigo} trabaja {info.grupo}, que no corresponde al día {enfoque} ({NOMBRES_DIAS[d.dia]})")
            continue
        if ej.codigo in vistos:
            errores.append(f"{ej.codigo} está repetido el {NOMBRES_DIAS[d.dia]}")
            continue
        vistos.add(ej.codigo)
        # PG-25: fuera de rango → se corrige al límite más cercano.
        s = min(max(ej.series, r["series"][0]), r["series"][1])
        if ctx.nivel == "principiante":
            s = min(s, SERIES_MAX_PRINCIPIANTE)
        rmin, rmax = sorted((ej.reps_min, ej.reps_max))
        rmin = min(max(rmin, r["reps"][0]), r["reps"][1])
        rmax = min(max(rmax, rmin), r["reps"][1])
        desc = min(max(ej.descanso_seg, r["descanso"][0]), r["descanso"][1])
        if (s, rmin, rmax, desc) != (ej.series, ej.reps_min, ej.reps_max, ej.descanso_seg):
            correcciones.append(f"{ej.codigo}: series/repeticiones/descanso ajustados a los rangos de tu objetivo")
        motivo = lenguaje_simple(_una_frase(ej.motivo)) or _motivo_reglas(ctx, info)
        limpios.append(EjercicioPlan(ej.codigo, s, rmin, rmax, desc, motivo, info.precaucion))
    if len(limpios) > ctx.n_ejercicios:
        correcciones.append(f"{NOMBRES_DIAS[d.dia]}: se dejaron {ctx.n_ejercicios} ejercicios para que entre en tus minutos")
        limpios = limpios[: ctx.n_ejercicios]
    posibles = len({e.codigo for g in grupos_permitidos for e in ctx.permitidos.values() if e.grupo == g})
    minimo = min(MIN_EJERCICIOS, posibles, ctx.n_ejercicios)
    if len(limpios) < minimo:
        errores.append(f"el {NOMBRES_DIAS[d.dia]} tiene {len(limpios)} ejercicios válidos y necesita al menos {minimo}")
    d.ejercicios = limpios
    d.grupos = list(dict.fromkeys(ctx.permitidos[e.codigo].grupo for e in limpios))
    faltan = [g for g in obligatorios if g not in d.grupos]
    if faltan:
        errores.append(f"el {NOMBRES_DIAS[d.dia]} debe incluir al menos un ejercicio de: {', '.join(faltan)}")
    explicacion = lenguaje_simple(_max_lineas(d.explicacion))
    if explicacion != " ".join((d.explicacion or "").split()):
        correcciones.append(f"{NOMBRES_DIAS[d.dia]}: explicación acortada o simplificada")
    d.explicacion = explicacion or _explicacion_dia_reglas(ctx, enfoque, d.grupos, [ctx.permitidos[e.codigo] for e in limpios])


def validar(plan: PlanPropuesto, ctx: Contexto) -> Revision:
    """Revisa TODO lo que no se negocia. Lo leve se corrige solo; lo grave rechaza el plan."""
    errores: list[str] = []
    correcciones: list[str] = []

    dias_plan = [d.dia for d in plan.dias]
    if sorted(dias_plan, key=lambda d: DIAS_SEMANA.index(d) if d in DIAS_SEMANA else 99) != ctx.dias:
        errores.append(f"los días deben ser exactamente {', '.join(ctx.dias)} (llegaron {', '.join(dias_plan) or 'ninguno'})")
        return Revision(None, errores, correcciones)
    plan.dias.sort(key=lambda d: DIAS_SEMANA.index(d.dia))

    for d in plan.dias:
        revisar_dia(d, ctx, errores, correcciones)

    # PG-24: nunca el mismo grupo principal en dos días seguidos.
    for a, b in itertools.combinations(plan.dias, 2):
        if son_seguidos(a.dia, b.dia):
            comunes = set(a.grupos) & set(b.grupos)
            if comunes:
                errores.append(f"{NOMBRES_DIAS[a.dia]} y {NOMBRES_DIAS[b.dia]} son seguidos y repiten {', '.join(sorted(comunes))}")

    # PG-23: cada grupo grande, al menos 1 vez por semana (salvo los que las lesiones impiden).
    trabajados = {g for d in plan.dias for g in d.grupos}
    faltan = [g for g in GRUPOS_GRANDES if g not in trabajados and g not in ctx.grupos_omitidos]
    if faltan and len(ctx.dias) > 1:
        errores.append(f"falta trabajar en la semana: {', '.join(faltan)}")

    # PG-27: explicación general simple y que mencione la lesión cuando aplica.
    general = lenguaje_simple(" ".join((plan.explicacion or "").split()))
    if len(general) > 700:
        general = _max_lineas(general, 5, 700)
        correcciones.append("explicación general acortada")
    if not general:
        general = _explicacion_reglas(ctx, "")
    if ctx.zonas and not any(sin_tildes(ctx.nombres_zonas.get(z, z)) in sin_tildes(general) for z in ctx.zonas):
        general = f"{general} {_texto_lesiones(ctx)}"
        correcciones.append("se agregó cómo se tuvo en cuenta la lesión")
    plan.explicacion = general
    return Revision(None if errores else plan, errores, correcciones)


def avisos_generales(ctx: Contexto) -> list[str]:
    avisos = [
        f"No incluimos ejercicios de {ctx.nombres_grupos.get(g, g).lower()}: {motivo}"
        for g, motivo in ctx.grupos_omitidos.items()
    ]
    if len(ctx.dias) == 1:
        avisos.append("Con 1 día por semana no alcanzamos a trabajar todos los músculos grandes. Si puedes, suma un día.")
    return avisos
