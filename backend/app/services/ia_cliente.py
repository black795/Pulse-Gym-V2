"""Cliente único de IA: lo usan el reconocimiento de fotos (PG-08), el plan (PG-23) y la adaptación (PG-28).

- Proveedor principal: Google Gemini (capa gratuita). Pide JSON con un esquema fijo (PG-26).
- Respaldo: Gemini 2.5 Flash en Replicate (REPLICATE_API_TOKEN, cobra por tokens). Acepta texto e imágenes. Se usa si
  Gemini falla (saturado, límite por minuto, sin clave) o tarda, y para las copias de los pedidos lentos.
- Nunca se pasa del tiempo total: antes, cada modelo tenía sus propios 15 s y en el peor caso se esperaba un minuto
  mientras la app ya había mostrado el error.
- Devuelve los tokens usados para calcular el costo estimado (PG-49).
"""
import json
import time
from collections.abc import Callable
from contextvars import ContextVar
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

MODELOS_RESPALDO = ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
REPLICATE_URL = "https://api.replicate.com/v1/models/{modelo}/predictions"

# True dentro del hilo de una copia lanzada por `carrera`: esa copia va primero al proveedor de respaldo.
_es_copia: ContextVar[bool] = ContextVar("es_copia", default=False)


class ErrorIA(Exception):
    """La IA falló, tardó demasiado o respondió algo que no se entiende."""


@dataclass
class RespuestaIA:
    modelo: str
    datos: object
    tokens_entrada: int = 0
    tokens_salida: int = 0


def como_respuesta(r: "RespuestaIA | tuple[str, object]") -> RespuestaIA:
    """Los proveedores simulados (y los de las pruebas) devuelven (modelo, datos); Gemini devuelve RespuestaIA."""
    return r if isinstance(r, RespuestaIA) else RespuestaIA(modelo=r[0], datos=r[1])


@dataclass
class Resultado:
    respuesta: object | None
    error: Exception | None
    duracion_ms: int


def carrera(tareas: dict[str, Callable[[float], object]], fin: float, duplicar_tras: float | None) -> tuple[dict[str, Resultado], int]:
    """Corre cada tarea en paralelo; cada una recibe los segundos que quedan hasta `fin` (time.perf_counter()).

    La capa gratuita de Gemini tiene tiempos muy irregulares: el MISMO pedido puede tardar 3 s o 30 s. Por eso, si una
    tarea no terminó a los `duplicar_tras` segundos, se lanza una copia (que va primero al proveedor de respaldo, si
    hay) y se usa la que termine primero.
    Devuelve los resultados por clave y cuántas copias se descartaron (para registrarlas en el costo, PG-49)."""
    inicio = time.perf_counter()
    hilos = ThreadPoolExecutor(max_workers=max(1, 2 * len(tareas)))
    corriendo: dict[Future, str] = {}

    def lanzar(clave: str, copia: bool = False) -> None:
        corriendo[hilos.submit(_medir, tareas[clave], fin, copia)] = clave

    for clave in tareas:
        lanzar(clave)
    resultados: dict[str, Resultado] = {}
    procesados: set[Future] = set()
    duplicadas = 0
    ya_duplico = duplicar_tras is None
    while True:
        for fut in [g for g in corriendo if g.done() and g not in procesados]:
            procesados.add(fut)
            clave = corriendo[fut]
            if clave in resultados:
                continue
            r = fut.result()
            if r.error is not None and any(c == clave and not g.done() for g, c in corriendo.items()):
                continue  # falló una copia, pero la otra sigue: se espera a la otra
            resultados[clave] = r
        ahora = time.perf_counter()
        if len(resultados) == len(tareas) or ahora >= fin:
            break
        if not ya_duplico and ahora - inicio >= duplicar_tras:
            ya_duplico = True
            for clave in tareas:
                if clave not in resultados and fin - ahora >= 2:
                    lanzar(clave, copia=True)
                    duplicadas += 1
        # Se espera también por los que ya terminaron y aún no se procesaron: así wait() vuelve de inmediato.
        pendientes = [g for g, c in corriendo.items() if g not in procesados and c not in resultados]
        if not pendientes:
            break
        espera = fin - ahora if ya_duplico else min(fin - ahora, inicio + duplicar_tras - ahora)
        wait(pendientes, timeout=max(espera, 0.01), return_when=FIRST_COMPLETED)
    hilos.shutdown(wait=False, cancel_futures=True)  # las copias que siguen corriendo terminan solas al llegar a `fin`
    for clave in tareas:
        if clave not in resultados:
            resultados[clave] = Resultado(None, ErrorIA(f"La IA tardó más de {int(fin - inicio)} segundos."),
                                          int((time.perf_counter() - inicio) * 1000))
    return resultados, duplicadas  # por cada copia lanzada, una de las dos respuestas se descarta


def _medir(tarea: Callable[[float], object], fin: float, copia: bool = False) -> Resultado:
    _es_copia.set(copia)  # cada hilo tiene su propio contexto
    inicio = time.perf_counter()
    try:
        return Resultado(tarea(max(fin - inicio, 0.5)), None, int((time.perf_counter() - inicio) * 1000))
    except Exception as e:  # noqa: BLE001  (se devuelve para que quien llama decida; incluye ErrorIA)
        return Resultado(None, e, int((time.perf_counter() - inicio) * 1000))


def _detalle_error(r: httpx.Response) -> str:
    try:
        d = r.json()
        return str(d.get("error", {}).get("message", "") if isinstance(d.get("error"), dict) else d.get("detail") or d.get("error") or "")[:150]
    except ValueError:
        return r.text[:150]


def _texto_a_json(texto: str) -> object:
    """Replicate no garantiza JSON puro: a veces lo envuelve en ```json … ```. Se toma desde la primera { hasta la última }."""
    texto = texto.strip()
    if not texto.startswith("{"):
        inicio, fin = texto.find("{"), texto.rfind("}")
        if inicio == -1 or fin <= inicio:
            raise ValueError("sin JSON")
        texto = texto[inicio: fin + 1]
    return json.loads(texto)


# ---------------- Google Gemini (proveedor principal) ----------------
def _gemini(modelo: str, partes: list[dict], esquema: dict, temperatura: float, limite: float) -> RespuestaIA:
    cfg = get_settings()
    cuerpo = {
        "contents": [{"parts": partes}],
        "generationConfig": {"temperature": temperatura, "responseMimeType": "application/json", "responseSchema": esquema},
    }
    try:
        r = httpx.post(URL.format(modelo=modelo), json=cuerpo, headers={"x-goog-api-key": cfg.gemini_api_key}, timeout=limite)
    except httpx.TimeoutException:
        raise ErrorIA(f"La IA tardó más de {int(limite)} segundos.")
    except httpx.HTTPError as e:
        raise ErrorIA(f"No se pudo conectar con la IA ({e.__class__.__name__}).")
    if r.status_code == 429:
        raise ErrorIA("Se alcanzó el límite gratuito de la IA por minuto. Espera un momento y reintenta.")
    if r.status_code != 200:
        raise ErrorIA(f"La IA respondió con error {r.status_code}: {_detalle_error(r)}")
    try:
        cuerpo_r = r.json()
        # Los modelos que "piensan" pueden devolver varias partes: se une solo el texto de la respuesta.
        partes_r = cuerpo_r["candidates"][0]["content"]["parts"]
        datos = json.loads("".join(p.get("text", "") for p in partes_r if not p.get("thought")))
    except (KeyError, IndexError, TypeError, ValueError):
        raise ErrorIA("La IA respondió algo que no se pudo entender.")
    uso = cuerpo_r.get("usageMetadata") or {}
    return RespuestaIA(
        modelo=modelo, datos=datos, tokens_entrada=int(uso.get("promptTokenCount") or 0),
        tokens_salida=int(uso.get("candidatesTokenCount") or 0) + int(uso.get("thoughtsTokenCount") or 0),
    )


# ---------------- Replicate (respaldo, cobra por tokens) ----------------
def _replicate(partes: list[dict], esquema: dict, temperatura: float, limite: float) -> RespuestaIA:
    """Gemini 2.5 Flash en Replicate: acepta texto e imágenes. No tiene "esquema fijo", así que el esquema se pone en
    el texto y la respuesta pasa por la misma validación de siempre (PG-26)."""
    cfg = get_settings()
    fin = time.perf_counter() + limite
    textos = [p["text"] for p in partes if "text" in p]
    imagenes = [f"data:{p['inline_data']['mime_type']};base64,{p['inline_data']['data']}" for p in partes if "inline_data" in p]
    prompt = "\n\n".join(textos) + (
        "\n\nResponde SOLO con un objeto JSON válido (sin texto antes ni después) que cumpla este esquema:\n"
        + json.dumps(esquema, ensure_ascii=False)
    )
    entrada = {"prompt": prompt, "temperature": temperatura, "thinking_budget": 0, "max_output_tokens": 4096}
    if imagenes:
        entrada["images"] = imagenes
    encabezados = {"Authorization": f"Bearer {cfg.replicate_api_token}", "Content-Type": "application/json"}
    modelo = f"replicate/{cfg.replicate_modelo}"
    try:
        for intento in range(2):
            restante = fin - time.perf_counter()
            r = httpx.post(
                REPLICATE_URL.format(modelo=cfg.replicate_modelo), json={"input": entrada},
                headers={**encabezados, "Prefer": f"wait={max(1, min(60, int(restante)))}"}, timeout=max(restante, 0.5),
            )
            if r.status_code != 429:
                break
            # Con menos de USD 5 de saldo, Replicate permite 6 pedidos por minuto y de a uno. Si dice cuándo
            # reintentar y el tiempo alcanza (dejando 3 s para la respuesta), se espera una vez.
            try:
                espera = float(r.json().get("retry_after") or r.headers.get("retry-after") or 99)
            except (ValueError, AttributeError):
                espera = 99
            if intento == 1 or espera + 3 > fin - time.perf_counter():
                raise ErrorIA("Replicate: se alcanzó el límite de pedidos por minuto.")
            time.sleep(espera)
        if r.status_code not in (200, 201):
            raise ErrorIA(f"Replicate respondió con error {r.status_code}: {_detalle_error(r)}")
        pred = r.json()
        # Si no terminó dentro de la espera, se consulta hasta que termine o se acabe el tiempo.
        while pred.get("status") in ("starting", "processing") and time.perf_counter() < fin - 0.5:
            time.sleep(0.4)
            pred = httpx.get(pred["urls"]["get"], headers=encabezados, timeout=max(fin - time.perf_counter(), 0.5)).json()
    except httpx.TimeoutException:
        raise ErrorIA(f"Replicate tardó más de {int(limite)} segundos.")
    except httpx.HTTPError as e:
        raise ErrorIA(f"No se pudo conectar con Replicate ({e.__class__.__name__}).")
    if pred.get("status") != "succeeded":
        if pred.get("status") in ("starting", "processing"):
            try:  # no se espera más: se cancela para no pagar por algo que nadie va a usar
                httpx.post(pred["urls"]["cancel"], headers=encabezados, timeout=3)
            except (httpx.HTTPError, KeyError):
                pass
            raise ErrorIA(f"Replicate tardó más de {int(limite)} segundos.")
        raise ErrorIA(f"Replicate no pudo responder: {str(pred.get('error') or pred.get('status'))[:150]}")
    salida = pred.get("output")
    try:
        datos = _texto_a_json("".join(salida) if isinstance(salida, list) else str(salida or ""))
    except ValueError:
        raise ErrorIA("La IA respondió algo que no se pudo entender.")
    m = pred.get("metrics") or {}
    return RespuestaIA(modelo=modelo, datos=datos, tokens_entrada=int(m.get("token_input_count") or 0),
                       tokens_salida=int(m.get("token_output_count") or 0))


def hay_respaldo() -> bool:
    return bool(get_settings().replicate_api_token)


def pedir_json(partes: list[dict], esquema: dict, *, limite_seg: float, temperatura: float = 0.1) -> RespuestaIA:
    """Prueba los proveedores en orden sin pasarse de `limite_seg` en total:
    Gemini (modelo configurado) → Replicate → los otros modelos de Gemini.
    Si hay respaldo, Gemini usa como mucho el 60 % del tiempo, para que a Replicate le quede margen.
    Las copias de `carrera` (pedidos que tardaban) van primero a Replicate: así la copia no espera en la misma fila."""
    cfg = get_settings()
    intentos: list[tuple[str, str]] = []
    if cfg.ia_proveedor != "replicate" and cfg.gemini_api_key:
        intentos.append(("gemini", cfg.gemini_modelo))
    if hay_respaldo():
        intentos.insert(0 if _es_copia.get() or cfg.ia_proveedor == "replicate" else len(intentos), ("replicate", cfg.replicate_modelo))
    if cfg.ia_proveedor != "replicate" and cfg.gemini_api_key:
        intentos += [("gemini", m) for m in MODELOS_RESPALDO if m != cfg.gemini_modelo]
    if not intentos:
        raise ErrorIA("Falta GEMINI_API_KEY (o REPLICATE_API_TOKEN) en el archivo .env del backend.")

    fin = time.perf_counter() + limite_seg
    ultimo_error: ErrorIA | None = None
    for i, (proveedor, modelo) in enumerate(intentos):
        restante = fin - time.perf_counter()
        if restante < 1:  # no alcanza el tiempo para probar otro
            break
        quedan_otros = any(p != proveedor for p, _ in intentos[i + 1:])
        limite = restante * 0.6 if quedan_otros and restante > 4 else restante
        try:
            if proveedor == "replicate":
                return _replicate(partes, esquema, temperatura, limite)
            return _gemini(modelo, partes, esquema, temperatura, limite)
        except ErrorIA as e:
            ultimo_error = e
    raise ultimo_error or ErrorIA(f"La IA tardó más de {int(limite_seg)} segundos.")
