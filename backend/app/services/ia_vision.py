"""PG-08: reconocer una máquina en una foto comparándola con nuestro catálogo.

Proveedores (variable IA_PROVEEDOR):
- "gemini": Google Gemini con visión. Tiene capa gratuita: crea una clave en https://aistudio.google.com/apikey
  y ponla en GEMINI_API_KEY. OJO: en la capa gratuita Google puede usar lo que envías para mejorar sus productos;
  sirve para probar, no para fotos de usuarios reales (PG-48).
- "simulada": no llama a nadie. Devuelve sugerencias inventadas (pero del catálogo real) para probar todo el flujo.
- "auto" (por defecto): Gemini si hay clave; si no, la simulada.

La IA solo puede proponer códigos del catálogo: todo lo demás se descarta aquí, no se confía en el modelo.
"""
import base64
import hashlib
import time
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.services import ia_cliente
from app.services.ia_cliente import ErrorIA, RespuestaIA  # noqa: F401  (ErrorIA se usa desde otros módulos)

MAX_SUGERENCIAS = 3


@dataclass
class MaquinaParaIA:
    codigo: str
    nombre: str
    otros_nombres: list[str]
    tipo: str


@dataclass
class ResultadoIA:
    modelo: str
    es_maquina_de_gym: bool
    sugerencias: list[tuple[str, float]] = field(default_factory=list)  # (codigo, confianza) de mayor a menor
    descartadas: int = 0  # códigos inventados por la IA que no están en el catálogo
    duracion_ms: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0


def limpiar_respuesta(datos: dict, codigos_validos: set[str]) -> tuple[bool, list[tuple[str, float]], int]:
    """Valida lo que respondió el modelo: solo códigos del catálogo, sin repetidos, confianza entre 0 y 1."""
    if not isinstance(datos, dict):
        raise ErrorIA("La IA respondió en un formato inesperado.")
    es_maquina = bool(datos.get("es_maquina_de_gym", False))
    vistas: dict[str, float] = {}
    descartadas = 0
    for s in datos.get("sugerencias") or []:
        if not isinstance(s, dict):
            descartadas += 1
            continue
        codigo = str(s.get("codigo", "")).strip().upper()
        try:
            confianza = min(max(float(s.get("confianza", 0)), 0.0), 1.0)
        except (TypeError, ValueError):
            confianza = 0.0
        if codigo not in codigos_validos:
            descartadas += 1
            continue
        vistas[codigo] = max(confianza, vistas.get(codigo, 0.0))
    ordenadas = sorted(vistas.items(), key=lambda t: t[1], reverse=True)[:MAX_SUGERENCIAS]
    return es_maquina, ordenadas, descartadas


# ---------------- Gemini ----------------
def _prompt(catalogo: list[MaquinaParaIA]) -> str:
    lineas = "\n".join(
        f"- {m.codigo} | {m.nombre} | también: {', '.join(m.otros_nombres) or '—'} | tipo: {m.tipo}" for m in catalogo
    )
    return (
        "Eres un experto en equipamiento de gimnasio. Mira la foto e identifica qué equipo es, "
        "eligiendo SOLO entre este catálogo (código | nombre | otros nombres | tipo):\n"
        f"{lineas}\n\n"
        "Responde en JSON con:\n"
        '- "es_maquina_de_gym": false si la foto no muestra equipo de gimnasio (una persona, un paisaje, comida, '
        "algo borroso donde no se distingue nada); true en otro caso.\n"
        '- "sugerencias": hasta 3 opciones del catálogo, de la más probable a la menos, cada una con "codigo" '
        '(exactamente como aparece arriba) y "confianza" entre 0 y 1. Sé honesto con la confianza: usa más de 0.85 '
        "solo si estás seguro; si dos máquinas se parecen (por ejemplo hack squat y prensa), baja la confianza. "
        "Si no es equipo de gimnasio, devuelve una lista vacía."
    )


def _esquema(codigos: list[str]) -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "es_maquina_de_gym": {"type": "BOOLEAN"},
            "sugerencias": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {"codigo": {"type": "STRING", "enum": codigos}, "confianza": {"type": "NUMBER"}},
                    "required": ["codigo", "confianza"],
                },
            },
        },
        "required": ["es_maquina_de_gym", "sugerencias"],
    }


def _gemini(imagen_jpg: bytes, catalogo: list[MaquinaParaIA]) -> RespuestaIA:
    partes = [
        {"text": _prompt(catalogo)},
        {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(imagen_jpg).decode("ascii")}},
    ]
    return ia_cliente.pedir_json(partes, _esquema([m.codigo for m in catalogo]), limite_seg=get_settings().ia_timeout_seg)


# ---------------- Simulada ----------------
def _simulada(imagen_jpg: bytes, catalogo: list[MaquinaParaIA]) -> tuple[str, dict]:
    """Elige 3 máquinas del catálogo según la foto (la misma foto da siempre lo mismo) con confianza media,
    para poder probar la pantalla de "elige la correcta" sin clave ni internet."""
    if not catalogo:
        return "simulada", {"es_maquina_de_gym": True, "sugerencias": []}
    n = int(hashlib.sha256(imagen_jpg).hexdigest(), 16)
    elegidas = [catalogo[(n + i * 7) % len(catalogo)].codigo for i in range(MAX_SUGERENCIAS)]
    confianzas = [0.62, 0.24, 0.09]
    return "simulada", {"es_maquina_de_gym": True, "sugerencias": [
        {"codigo": c, "confianza": p} for c, p in zip(elegidas, confianzas)
    ]}


PROVEEDORES = {"gemini": _gemini, "simulada": _simulada}


def reconocer(imagen_jpg: bytes, catalogo: list[MaquinaParaIA]) -> ResultadoIA:
    proveedor = PROVEEDORES.get(get_settings().ia_proveedor_efectivo)
    if proveedor is None:
        raise ErrorIA("IA_PROVEEDOR no válido (usa auto, gemini o simulada).")
    inicio = time.perf_counter()
    r = ia_cliente.como_respuesta(proveedor(imagen_jpg, catalogo))
    es_maquina, sugerencias, descartadas = limpiar_respuesta(r.datos, {m.codigo for m in catalogo})
    return ResultadoIA(
        modelo=r.modelo, es_maquina_de_gym=es_maquina, sugerencias=sugerencias if es_maquina else [],
        descartadas=descartadas, duracion_ms=int((time.perf_counter() - inicio) * 1000),
        tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida,
    )
