"""La IA del plan (PG-23, PG-27) y de la adaptación del día (PG-28): elige, ordena y explica DENTRO de los límites
que fijan las reglas (plan_reglas.py). Nunca decide qué es seguro: solo puede usar códigos que las reglas le dan, y
lo que responde se valida igual (PG-26). El plan se pide en paralelo (una llamada corta por día y otra para la
explicación general): así llega en menos de 20 s aunque el modelo sea lento.

Proveedores, igual que en el reconocimiento de fotos: "gemini" (real) o "simulada" (sin internet, para probar).
Privacidad: a la IA se le envía objetivo, nivel, edad, sexo, composición corporal y la ZONA de cada lesión; nunca el
nombre, el correo ni las descripciones que escribió el usuario.
"""
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.services import ia_cliente, plan_reglas as reglas
from app.services.ia_cliente import ErrorIA, RespuestaIA

TEXTO_NIVEL = {"principiante": "principiante (empieza o retoma)", "intermedio": "intermedio", "avanzado": "avanzado"}
TEXTO_EQUIPO = {"maquina": "máquina", "peso_libre": "peso libre", "sin_equipo": "sin equipo"}
MAX_CANDIDATOS_POR_GRUPO = 10


class ErrorFormato(ValueError):
    """PG-26: la respuesta no tiene el formato JSON fijo."""


# ---------------- Formato fijo de la respuesta (PG-26) ----------------
# La IA NO escribe series, repeticiones ni descansos: los pone el sistema según PG-25. Así la respuesta es corta y
# llega a tiempo (la capa gratuita de Gemini puede generar apenas ~30 tokens por segundo).
class _EjercicioIA(BaseModel):
    codigo: str
    motivo: str = ""


class _DiaIA(BaseModel):
    explicacion: str = ""
    ejercicios: list[_EjercicioIA]


class _GeneralIA(BaseModel):
    explicacion: str


@dataclass
class Pedido:
    """Una de las llamadas en paralelo del plan: la explicación general o un día."""
    tipo: str  # general | dia
    dia: str | None = None
    base: reglas.DiaPlan | None = None  # propuesta de reglas para ese día (y respaldo si la IA falla)
    obligatorios: list[str] = field(default_factory=list)  # grupos grandes que el día debe incluir
    otros: dict[str, list[str]] = field(default_factory=dict)  # otros días con el mismo enfoque → sus ejercicios
    errores_previos: list[str] = field(default_factory=list)

    @property
    def clave(self) -> str:
        return self.dia or "general"


def _error_formato(e: ValidationError) -> ErrorFormato:
    campos = ", ".join(".".join(str(x) for x in err["loc"]) for err in e.errors()[:5])
    return ErrorFormato(f"formato JSON inválido ({campos or 'respuesta'})")


def interpretar_dia(datos: object, ctx: reglas.Contexto, pedido: Pedido) -> reglas.DiaPlan:
    try:
        d = _DiaIA.model_validate(datos)
    except ValidationError as e:
        raise _error_formato(e)
    ejercicios = []
    for e in d.ejercicios:
        info = ctx.permitidos.get(e.codigo)
        series, rmin, rmax, descanso = reglas.prescripcion(ctx.objetivo_tipo, ctx.nivel, info.multiarticular if info else True)
        ejercicios.append(reglas.EjercicioPlan(e.codigo, series, rmin, rmax, descanso, e.motivo))
    return reglas.DiaPlan(dia=pedido.dia or "", enfoque="", grupos=[], explicacion=d.explicacion, ejercicios=ejercicios)


def interpretar_general(datos: object) -> str:
    try:
        return _GeneralIA.model_validate(datos).explicacion
    except ValidationError as e:
        raise _error_formato(e)


def a_json_dia(d: reglas.DiaPlan) -> dict:
    return {"explicacion": d.explicacion, "ejercicios": [{"codigo": e.codigo, "motivo": e.motivo} for e in d.ejercicios]}


# ---------------- Plan semanal ----------------
def _texto_perfil(ctx: reglas.Contexto) -> str:
    p = ctx.perfil
    datos = [
        f"objetivo: {reglas.TEXTO_OBJETIVO.get(ctx.objetivo, ctx.objetivo)}",
        f"nivel: {TEXTO_NIVEL.get(ctx.nivel, ctx.nivel)}", f"{ctx.minutos} minutos por sesión",
    ]
    for clave, texto in (("edad", "edad {} años"), ("sexo", "sexo {}"), ("peso_kg", "peso {} kg"),
                         ("grasa_pct", "{} % de grasa"), ("masa_muscular_kg", "masa muscular {} kg")):
        if p.get(clave) is not None:
            datos.append(texto.format(p[clave]))
    return ", ".join(datos)


def _texto_lesiones(ctx: reglas.Contexto) -> str:
    if not ctx.zonas:
        return "ninguna"
    estados = {"activa": "activa: ya quitamos todo lo que la carga", "reintroduccion": "en recuperación: los marcados [precaución] van suaves"}
    return "; ".join(f"{ctx.nombres_zonas.get(z, z)} ({estados[e]})" for z, e in ctx.zonas.items())


def _rechazo(errores: list[str]) -> str:
    if not errores:
        return ""
    return "\n\nTU RESPUESTA ANTERIOR FUE RECHAZADA por estos motivos; corrígelos:\n- " + "\n- ".join(errores[:8])


def codigos_del_dia(ctx: reglas.Contexto, dia: str) -> list[str]:
    return sorted(e.codigo for opciones in reglas.candidatos_del_dia(ctx, dia).values() for e in opciones)


def prompt_dia(ctx: reglas.Contexto, pedido: Pedido) -> str:
    enfoque = reglas.PLANTILLAS[ctx.plantilla_por_dia[pedido.dia]][0]
    bloques = []
    for g, ejercicios in reglas.candidatos_del_dia(ctx, pedido.dia).items():
        if not ejercicios:
            continue
        lineas = "\n".join(
            f"  - {e.codigo} | {e.nombre} | {'varias articulaciones' if e.multiarticular else 'una articulación'} | "
            f"{e.dificultad} | {TEXTO_EQUIPO.get(e.categoria, e.categoria)}{' | [precaución]' if e.precaucion else ''}"
            for e in ejercicios[:MAX_CANDIDATOS_POR_GRUPO]
        )
        bloques.append(f"{g} ({ctx.nombres_grupos.get(g, g)}):\n{lineas}")
    otros = "".join(
        f"\n- El {reglas.NOMBRES_DIAS[d].lower()} también es «{enfoque}» y usa: {', '.join(c)}. Prefiere variar."
        for d, c in pedido.otros.items()
    )
    base = ", ".join(e.codigo for e in pedido.base.ejercicios) if pedido.base else ""
    obligatorios = f"- Incluye al menos un ejercicio de cada grupo: {', '.join(pedido.obligatorios)}.\n" if pedido.obligatorios else ""
    lesion = ", diciendo cómo cuidaste su lesión si afecta este día" if ctx.zonas else ""
    return (
        f"Eres un entrenador personal. Elige y ordena los ejercicios del {reglas.NOMBRES_DIAS[pedido.dia].lower()} "
        f"(«{enfoque}») para esta persona y explícalos.\n\n"
        f"Persona: {_texto_perfil(ctx)}.\nLesiones: {_texto_lesiones(ctx)}.\n\n"
        "Reglas que NO puedes cambiar:\n"
        f"- Entre {min(reglas.MIN_EJERCICIOS, ctx.n_ejercicios)} y {ctx.n_ejercicios} ejercicios, sin repetir. "
        "Primero los básicos (los que mueven varias articulaciones).\n"
        f"{obligatorios}"
        "- Usa SOLO ejercicios de esta lista (código | nombre | tipo | dificultad | equipo):\n" + "\n".join(bloques) + "\n"
        f"- Propuesta del sistema (cámbiala solo si algo le sirve más a esta persona): {base}.{otros}\n"
        "- Las series, repeticiones y descansos los pone el sistema: NO los escribas.\n\n"
        "Explica en español simple, como a alguien que no sabe de gimnasio y sin términos técnicos:\n"
        f'- "explicacion": máximo 2 frases sobre el día{lesion}.\n'
        '- "motivo": UNA frase de máximo 12 palabras por ejercicio.'
        + _rechazo(pedido.errores_previos)
    )


def esquema_dia(ctx: reglas.Contexto, dia: str) -> dict:
    ejercicio = {
        "type": "OBJECT",
        "properties": {"codigo": {"type": "STRING", "enum": codigos_del_dia(ctx, dia)}, "motivo": {"type": "STRING"}},
        "required": ["codigo", "motivo"],
    }
    return {
        "type": "OBJECT",
        "properties": {"explicacion": {"type": "STRING"}, "ejercicios": {"type": "ARRAY", "items": ejercicio}},
        "required": ["explicacion", "ejercicios"],
    }


def prompt_general(ctx: reglas.Contexto) -> str:
    dias = ", ".join(f"{reglas.NOMBRES_DIAS[d].lower()}: {reglas.PLANTILLAS[ctx.plantilla_por_dia[d]][0]}" for d in ctx.dias)
    lesion = " y cómo cuidamos su lesión" if ctx.zonas else ""
    return (
        "Eres un entrenador personal. En 2 o 3 frases simples, sin términos técnicos, explícale a esta persona por qué "
        f"su plan semanal le sirve.\n\nPersona: {_texto_perfil(ctx)}.\nLesiones: {_texto_lesiones(ctx)}.\n"
        f"Plan: {len(ctx.dias)} días con un esquema de {reglas.TEXTO_ESQUEMA[ctx.esquema]} ({dias}).\n"
        f'Menciona su objetivo{lesion}. Responde en "explicacion".'
    )


ESQUEMA_GENERAL = {"type": "OBJECT", "properties": {"explicacion": {"type": "STRING"}}, "required": ["explicacion"]}


def _plan_gemini(ctx: reglas.Contexto, pedido: Pedido, limite_seg: float) -> RespuestaIA:
    if pedido.tipo == "general":
        return ia_cliente.pedir_json([{"text": prompt_general(ctx)}], ESQUEMA_GENERAL, limite_seg=limite_seg, temperatura=0.4)
    return ia_cliente.pedir_json(
        [{"text": prompt_dia(ctx, pedido)}], esquema_dia(ctx, pedido.dia), limite_seg=limite_seg, temperatura=0.4,
    )


def _plan_simulada(ctx: reglas.Contexto, pedido: Pedido, limite_seg: float) -> tuple[str, dict]:
    """Sin internet: devuelve la propuesta de reglas como si la hubiera elegido la IA (para probar las pantallas)."""
    if pedido.tipo == "general":
        return "simulada", {"explicacion": "(IA simulada) " + reglas.armar_con_reglas(ctx).explicacion}
    return "simulada", a_json_dia(pedido.base)


PROVEEDORES_PLAN = {"gemini": _plan_gemini, "simulada": _plan_simulada}


def proponer(ctx: reglas.Contexto, pedido: Pedido, limite_seg: float) -> RespuestaIA:
    proveedor = PROVEEDORES_PLAN.get(get_settings().ia_proveedor_efectivo)
    if proveedor is None:
        raise ErrorIA("IA_PROVEEDOR no válido (usa auto, gemini o simulada).")
    return ia_cliente.como_respuesta(proveedor(ctx, pedido, limite_seg))


# ---------------- Adaptación del día (PG-28) ----------------
def prompt_adaptacion(enfoque: str, gym: str, cambios: list[dict]) -> str:
    bloques = []
    for c in cambios:
        opciones = "\n".join(
            f"    - {o['codigo']} | {o['nombre']} | {TEXTO_EQUIPO.get(o['categoria'], o['categoria'])}"
            f"{' | [precaución]' if o['precaucion'] else ''}" for o in c["opciones"]
        )
        bloques.append(f"- {c['codigo']} ({c['nombre']}, trabaja {c['grupo']}). Por qué no se puede: {c['motivo']}\n  Opciones:\n{opciones}")
    return (
        f"Hoy toca «{enfoque}» en «{gym}». Estos ejercicios del plan no se pueden hacer ahí. Para cada uno elige "
        "UN reemplazo de SUS opciones (el que mejor trabaje el mismo músculo con lo que hay) y explica en UNA frase "
        "simple, sin términos técnicos, por qué ese.\n\n" + "\n".join(bloques)
    )


def esquema_adaptacion(cambios: list[dict]) -> dict:
    return {
        "type": "OBJECT",
        "properties": {"cambios": {"type": "ARRAY", "items": {
            "type": "OBJECT",
            "properties": {
                "original": {"type": "STRING", "enum": [c["codigo"] for c in cambios]},
                "reemplazo": {"type": "STRING", "enum": sorted({o["codigo"] for c in cambios for o in c["opciones"]})},
                "motivo": {"type": "STRING"},
            },
            "required": ["original", "reemplazo", "motivo"],
        }}},
        "required": ["cambios"],
    }


def _adaptar_gemini(enfoque: str, gym: str, cambios: list[dict], limite_seg: float) -> RespuestaIA:
    return ia_cliente.pedir_json(
        [{"text": prompt_adaptacion(enfoque, gym, cambios)}], esquema_adaptacion(cambios), limite_seg=limite_seg,
    )


def _adaptar_simulada(enfoque: str, gym: str, cambios: list[dict], limite_seg: float) -> tuple[str, dict]:
    return "simulada", {"cambios": [
        {"original": c["codigo"], "reemplazo": c["opciones"][0]["codigo"],
         "motivo": f"(IA simulada) Trabaja {c['grupo']} con lo que hay en este gym."}
        for c in cambios
    ]}


PROVEEDORES_ADAPTACION = {"gemini": _adaptar_gemini, "simulada": _adaptar_simulada}


def proponer_adaptacion(enfoque: str, gym: str, cambios: list[dict], limite_seg: float) -> RespuestaIA:
    proveedor = PROVEEDORES_ADAPTACION.get(get_settings().ia_proveedor_efectivo)
    if proveedor is None:
        raise ErrorIA("IA_PROVEEDOR no válido (usa auto, gemini o simulada).")
    return ia_cliente.como_respuesta(proveedor(enfoque, gym, cambios, limite_seg))
