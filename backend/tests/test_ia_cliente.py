"""Cliente de IA: respaldo con Replicate cuando Gemini falla o tarda (sin llamar a internet)."""
import time

import pytest

from app.core.config import get_settings
from app.services import ia_cliente
from app.services.ia_cliente import ErrorIA


class Resp:
    def __init__(self, status: int, datos: dict):
        self.status_code, self._datos, self.text = status, datos, str(datos)

    def json(self):
        return self._datos


def gemini_ok(texto='{"ok": true}'):
    return Resp(200, {"candidates": [{"content": {"parts": [{"text": texto}]}}],
                      "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5}})


def replicate_ok(salida=('```json\n{"ok": ', 'true}\n```')):
    return Resp(201, {"status": "succeeded", "output": list(salida), "urls": {},
                      "metrics": {"token_input_count": 40, "token_output_count": 8}})


@pytest.fixture()
def red(monkeypatch):
    """red(gemini=..., replicate=...) → respuestas falsas por proveedor. Cada valor: Resp, excepción o función."""
    llamadas: list[tuple[str, dict]] = []

    def _fijar(gemini=None, replicate=None, token="r8_prueba", clave="clave-gemini"):
        monkeypatch.setattr(get_settings(), "replicate_api_token", token)
        monkeypatch.setattr(get_settings(), "gemini_api_key", clave)
        monkeypatch.setattr(get_settings(), "ia_proveedor", "auto")

        def post(url, json=None, headers=None, timeout=None):
            quien = "replicate" if "replicate.com" in url else "gemini"
            llamadas.append((quien, json))
            r = {"gemini": gemini, "replicate": replicate}[quien]
            if callable(r) and not isinstance(r, Resp):
                r = r(timeout)
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(ia_cliente.httpx, "post", post)
        return llamadas

    return _fijar


ESQUEMA = {"type": "OBJECT", "properties": {"ok": {"type": "BOOLEAN"}}}


@pytest.mark.parametrize(("respuesta", "mensaje"), [
    (Resp(503, {"error": {"message": "marcador-sintetico-privado"}}),
     "La IA respondió con error 503: marcador-sintetico-privado"),
    (Resp(429, {}), "Se alcanzó el límite gratuito de la IA por minuto. Espera un momento y reintenta."),
    (Resp(200, {}), "La IA respondió algo que no se pudo entender."),
])
def test_mensajes_actuales_de_gemini_no_cambian(red, respuesta, mensaje):
    red(gemini=respuesta)
    with pytest.raises(ErrorIA) as exc:
        ia_cliente._gemini("modelo-prueba", [], ESQUEMA, 0.1, 5)
    assert str(exc.value) == mensaje


def test_mensaje_actual_de_replicate_no_cambia(red):
    red(replicate=Resp(503, {"detail": "marcador-sintetico-privado"}))
    with pytest.raises(ErrorIA) as exc:
        ia_cliente._replicate([], ESQUEMA, 0.1, 5)
    assert str(exc.value) == "Replicate respondió con error 503: marcador-sintetico-privado"


@pytest.mark.parametrize(("respuesta", "categoria"), [
    (Resp(503, {"error": {"message": "marcador-sintetico-privado"}}), "ERROR_PROVEEDOR"),
    (Resp(429, {}), "LIMITE_PROVEEDOR"),
    (Resp(200, {}), "RESPUESTA_INVALIDA"),
    (ia_cliente.httpx.ConnectError("marcador-sintetico-privado"), "CONEXION"),
    (ia_cliente.httpx.ReadTimeout("marcador-sintetico-privado"), "TIMEOUT"),
])
def test_gemini_clasifica_errores_sin_alterar_su_mensaje(red, respuesta, categoria):
    red(gemini=respuesta)
    with pytest.raises(ErrorIA) as exc:
        ia_cliente._gemini("modelo-prueba", [], ESQUEMA, 0.1, 5)
    assert exc.value.categoria == categoria


@pytest.mark.parametrize(("respuesta", "categoria"), [
    (Resp(503, {"detail": "marcador-sintetico-privado"}), "ERROR_PROVEEDOR"),
    (Resp(429, {"retry_after": 99}), "LIMITE_PROVEEDOR"),
    (Resp(201, {"status": "succeeded", "output": "invalido"}), "RESPUESTA_INVALIDA"),
    (ia_cliente.httpx.ConnectError("marcador-sintetico-privado"), "CONEXION"),
    (ia_cliente.httpx.ReadTimeout("marcador-sintetico-privado"), "TIMEOUT"),
])
def test_replicate_clasifica_errores(red, respuesta, categoria):
    red(replicate=respuesta)
    with pytest.raises(ErrorIA) as exc:
        ia_cliente._replicate([], ESQUEMA, 0.1, 5)
    assert exc.value.categoria == categoria


def test_error_ia_conserva_argumentos_y_restringe_la_categoria():
    error = ErrorIA("mensaje", 7, categoria="marcador-sintetico-privado")
    assert str(error) == str(Exception("mensaje", 7))
    assert error.categoria == "ERROR_PROVEEDOR"


def test_si_gemini_responde_no_se_usa_replicate(red):
    llamadas = red(gemini=gemini_ok(), replicate=replicate_ok())
    r = ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=10)
    assert r.datos == {"ok": True} and r.modelo == get_settings().gemini_modelo
    assert [q for q, _ in llamadas] == ["gemini"]


@pytest.mark.parametrize("falla", [Resp(503, {"error": {"message": "high demand"}}), Resp(429, {}),
                                   ia_cliente.httpx.ConnectError("sin red")])
def test_si_gemini_falla_se_usa_replicate(red, falla):
    llamadas = red(gemini=falla, replicate=replicate_ok())
    r = ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=10)
    assert r.datos == {"ok": True}  # el JSON envuelto en ```json … ``` se entiende igual
    assert r.modelo == "replicate/google/gemini-2.5-flash" and (r.tokens_entrada, r.tokens_salida) == (40, 8)
    assert [q for q, _ in llamadas] == ["gemini", "replicate"]


def test_replicate_recibe_el_esquema_en_el_texto_y_las_fotos_como_imagenes(red):
    llamadas = red(gemini=Resp(503, {}), replicate=replicate_ok())
    ia_cliente.pedir_json([{"text": "¿qué máquina es?"}, {"inline_data": {"mime_type": "image/jpeg", "data": "QUJD"}}],
                          ESQUEMA, limite_seg=10)
    entrada = llamadas[1][1]["input"]
    assert entrada["images"] == ["data:image/jpeg;base64,QUJD"] and '"ok"' in entrada["prompt"]
    assert entrada["thinking_budget"] == 0  # sin "pensar": responde más rápido


def test_si_gemini_tarda_le_deja_tiempo_a_replicate(red):
    tiempos = []

    def lenta(timeout):
        tiempos.append(timeout)
        raise ia_cliente.httpx.ReadTimeout("lento")

    red(gemini=lenta, replicate=replicate_ok())
    r = ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=10)
    assert r.modelo.startswith("replicate/") and tiempos[0] == pytest.approx(6, abs=0.2)  # 60 % del tiempo


def test_sin_token_de_replicate_no_hay_respaldo(red):
    llamadas = red(gemini=Resp(503, {}), replicate=replicate_ok(), token="")
    with pytest.raises(ErrorIA):
        ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=3)
    assert all(q == "gemini" for q, _ in llamadas)


def test_si_los_dos_fallan_es_un_error_claro(red):
    red(gemini=Resp(503, {}), replicate=Resp(429, {"detail": "throttled"}))
    with pytest.raises(ErrorIA):
        ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=3)


def test_proveedor_replicate_usa_solo_replicate(red, monkeypatch):
    llamadas = red(gemini=gemini_ok(), replicate=replicate_ok())
    monkeypatch.setattr(get_settings(), "ia_proveedor", "replicate")
    assert ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=10).modelo.startswith("replicate/")
    assert [q for q, _ in llamadas] == ["replicate"]


def test_la_copia_de_un_pedido_lento_va_primero_a_replicate(red):
    def gemini_lenta(timeout):
        time.sleep(min(timeout, 1.5))
        return gemini_ok()

    llamadas = red(gemini=gemini_lenta, replicate=replicate_ok())
    inicio = time.perf_counter()
    resultados, copias = ia_cliente.carrera(
        {"dia": lambda limite: ia_cliente.pedir_json([{"text": "hola"}], ESQUEMA, limite_seg=limite)},
        time.perf_counter() + 5, duplicar_tras=0.2,
    )
    assert copias == 1 and time.perf_counter() - inicio < 1.0
    assert resultados["dia"].respuesta.modelo.startswith("replicate/")
    assert [q for q, _ in llamadas][:2] == ["gemini", "replicate"]


def test_el_costo_de_replicate_usa_su_propio_precio(monkeypatch):
    from app.services import ia_uso_service

    monkeypatch.setattr(get_settings(), "replicate_precio_entrada_usd_millon", 1.0)
    monkeypatch.setattr(get_settings(), "replicate_precio_salida_usd_millon", 10.0)
    assert ia_uso_service.costo(1000, 100, "replicate/google/gemini-2.5-flash") == pytest.approx(0.002)
