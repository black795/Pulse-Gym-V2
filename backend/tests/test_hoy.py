"""PG-28 (elegir el gym y adaptar la sesión del día) y PG-49 (límites de IA en fotos)."""
import pytest

from app.core.config import get_settings
from app.db.base import ahora
from app.models import Ejercicio, LlamadaIA, MaquinaCatalogo
from app.models.plan import DIAS_SEMANA
from app.services import ia_uso_service, ia_vision, plan_ia
from tests.conftest import imagen

HOY = DIAS_SEMANA[ahora().date().weekday()]


def dia_mas(n: int) -> str:
    return DIAS_SEMANA[(DIAS_SEMANA.index(HOY) + n) % 7]


@pytest.fixture()
def cfg(monkeypatch):
    ia_uso_service._alerta_enviada = None
    return lambda **v: [monkeypatch.setattr(get_settings(), k, x) for k, x in v.items()]


@pytest.fixture()
def con_plan(client, con_consentimiento):
    """con_plan(dias) → encabezados de una cuenta con perfil completo y plan armado para esos días."""

    def _crear(dias=None, email="ana@pulsegym.app") -> dict:
        h = con_consentimiento(email)
        client.put("/api/perfil", json={"objetivo": "ganar_musculo", "nivel": "intermedio", "dias_por_semana": 2,
                                        "minutos_por_sesion": 60}, headers=h)
        r = client.post("/api/plan", json={"dias": dias or [HOY, dia_mas(3)]}, headers=h)
        assert r.status_code == 201, r.text
        return h

    return _crear


def nuevo_gym(client, h, nombre="Gym Centro", maquinas=(), implementos=()):
    gid = client.post("/api/gyms", json={"nombre": nombre}, headers=h).json()["id"]
    if implementos:
        client.put(f"/api/gyms/{gid}/implementos", json={"implementos": list(implementos)}, headers=h)
    for codigo in maquinas:
        fid = client.post(f"/api/gyms/{gid}/fotos", files={"archivo": ("m.jpg", imagen(), "image/jpeg")}, headers=h).json()["id"]
        r = client.post(f"/api/fotos/{fid}/confirmar", json={"codigo": codigo, "origen": "manual"}, headers=h)
        assert r.status_code == 200, r.text
    return gid


def hoy(client, h, **params):
    r = client.get("/api/hoy", params={"fecha": ahora().date().isoformat(), **params}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def plan_de_hoy(client, h):
    plan = client.get("/api/plan", headers=h).json()["plan"]
    return next(d for d in plan["dias"] if d["dia"] == HOY)


def gym_completo(client, h, db, dia):
    """Un gym con todas las máquinas que usa el día del plan."""
    codigos = {m for e in dia["ejercicios"] for m in db.query(Ejercicio).filter_by(codigo=e["ejercicio"]["codigo"]).one().maquinas}
    maquinas = sorted({x.maquina.codigo for x in codigos})
    return nuevo_gym(client, h, maquinas=maquinas)


def test_sin_plan_no_hay_sesion(client, registrar):
    d = hoy(client, registrar())
    assert d["plan_existe"] is False and d["sesion"] is None and d["dia"] == HOY


def test_con_un_solo_gym_se_salta_la_eleccion_y_si_tiene_todo_no_cambia_nada(client, con_plan, db):
    h = con_plan()
    gid = gym_completo(client, h, db, plan_de_hoy(client, h))
    d = hoy(client, h)
    assert not d["requiere_elegir_gym"] and d["es_dia_de_entreno"]
    s = d["sesion"]
    assert s["gym_id"] == gid and s["cambios"] == 0 and not s["omitidos"]
    assert [e["ejercicio"]["codigo"] for e in s["ejercicios"]] == [e["ejercicio"]["codigo"] for e in plan_de_hoy(client, h)["ejercicios"]]
    assert s["duracion_ms"] < 10_000 and s["minutos_estimados"] > 0


def test_con_varios_gyms_primero_se_elige_y_el_ultimo_usado_va_primero(client, con_plan):
    h = con_plan()
    a = nuevo_gym(client, h, "Gym A")
    b = nuevo_gym(client, h, "Gym B")
    client.post(f"/api/gyms/{b}/usar", headers=h)
    d = hoy(client, h)
    assert d["requiere_elegir_gym"] and d["sesion"] is None
    assert [g["id"] for g in d["gyms"]] == [b, a] and d["gyms"][0]["es_ultimo_usado"]
    # Se puede cambiar de gym y la sesión se vuelve a adaptar.
    assert hoy(client, h, gym_id=b)["sesion"]["gym_nombre"] == "Gym B"
    assert hoy(client, h, gym_id=a)["sesion"]["gym_nombre"] == "Gym A"


def test_gym_sin_maquinas_usa_solo_ejercicios_sin_equipo_y_sugiere_fotos(client, con_plan):
    h = con_plan()
    nuevo_gym(client, h, "Mi casa")
    s = hoy(client, h)["sesion"]
    assert s["sugerir_fotos"] and any("fotos" in a.lower() for a in s["avisos"])
    assert all(e["ejercicio"]["categoria_equipo"] == "sin_equipo" for e in s["ejercicios"])
    for e in s["ejercicios"]:
        if e["cambio"]:
            assert e["original"] and "sin equipo" in e["motivo_cambio"] and e["por_que_reemplazo"]


def test_si_falta_una_maquina_se_usa_otra_del_mismo_musculo_y_se_explica_por_que(client, con_plan, db):
    h = con_plan()
    dia = plan_de_hoy(client, h)
    con_maquina = next(e for e in dia["ejercicios"] if e["ejercicio"]["categoria_equipo"] != "sin_equipo")
    gid = gym_completo(client, h, db, dia)
    # Se maloga la máquina de ese ejercicio.
    ej = db.query(Ejercicio).filter_by(codigo=con_maquina["ejercicio"]["codigo"]).one()
    detalle = client.get(f"/api/gyms/{gid}", headers=h).json()
    codigos_ej = {x.maquina.codigo for x in ej.maquinas}
    for gm in detalle["inventario"]:
        if gm["maquina"]["codigo"] in codigos_ej:
            client.patch(f"/api/gyms/{gid}/maquinas/{gm['id']}", json={"estado": "malograda"}, headers=h)
    s = hoy(client, h)["sesion"]
    cambiado = next(e for e in s["ejercicios"] if e["original"] and e["original"]["codigo"] == ej.codigo)
    assert cambiado["cambio"] and "malograda" in cambiado["motivo_cambio"]
    assert cambiado["ejercicio"]["musculo_principal"] == cambiado["original"]["musculo_principal"]
    assert s["cambios"] >= 1 and len({e["ejercicio"]["codigo"] for e in s["ejercicios"]}) == len(s["ejercicios"])


def test_si_hoy_no_toca_se_ofrece_adelantar_el_siguiente_dia(client, con_plan):
    h = con_plan([dia_mas(2), dia_mas(5)])
    nuevo_gym(client, h)
    d = hoy(client, h)
    assert not d["es_dia_de_entreno"] and d["sesion"] is None
    assert d["siguiente_dia"]["dia"] == dia_mas(2)
    adelantado = hoy(client, h, dia=dia_mas(2))
    assert adelantado["sesion"]["dia"] == dia_mas(2)
    r = client.get("/api/hoy", params={"dia": dia_mas(1)}, headers=h)
    assert r.status_code == 400  # ese día no está en el plan


def test_la_adaptacion_se_reutiliza_si_nada_cambio_y_se_rehace_si_cambia_el_inventario(client, con_plan, db):
    h = con_plan()
    gid = nuevo_gym(client, h)

    def llamadas():
        db.expire_all()
        return db.query(LlamadaIA).filter_by(tipo="adaptacion").count()

    primera = hoy(client, h)["sesion"]
    n = llamadas()
    assert n == 1 and primera["origen"] == "ia"
    assert hoy(client, h)["sesion"] == primera and llamadas() == n  # sin nueva llamada a la IA
    client.put(f"/api/gyms/{gid}/implementos", json={"implementos": ["mancuernas", "banco_plano"]}, headers=h)
    segunda = hoy(client, h)["sesion"]
    assert llamadas() == n + 1 and segunda != primera


def test_la_ia_solo_puede_elegir_entre_los_reemplazos_validos(client, con_plan, db, monkeypatch):
    monkeypatch.setitem(plan_ia.PROVEEDORES_ADAPTACION, "simulada", lambda enfoque, gym, cambios, limite: (
        "modelo-prueba", {"cambios": [{"original": c["codigo"], "reemplazo": "PRENSA_45", "motivo": "x."} for c in cambios]},
    ))
    h = con_plan()
    nuevo_gym(client, h)  # sin máquinas: PRENSA_45 nunca es válida aquí
    s = hoy(client, h)["sesion"]
    assert all(e["ejercicio"]["codigo"] != "PRENSA_45" for e in s["ejercicios"])
    db.expire_all()
    llamada = db.query(LlamadaIA).filter_by(tipo="adaptacion").one()
    assert llamada.resultado == "rechazada" and "PRENSA_45" in llamada.detalle


def test_la_adaptacion_respeta_las_lesiones(client, con_plan, db):
    h = con_plan()
    nuevo_gym(client, h, implementos=["mancuernas", "barra", "discos", "banco_plano", "rack"])
    client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=h)
    s = hoy(client, h)["sesion"]
    prohibidos = {e.codigo for e in db.query(Ejercicio) if any(c.zona.codigo == "hombro" for c in e.contraindicaciones)}
    assert not prohibidos & {e["ejercicio"]["codigo"] for e in s["ejercicios"]}


def test_el_gym_de_otra_persona_no_existe(client, con_plan):
    h = con_plan()
    otro = con_plan(email="beto@pulsegym.app")
    gid = nuevo_gym(client, otro)
    r = client.get("/api/hoy", params={"gym_id": gid}, headers=h)
    assert r.status_code == 404


def test_si_la_ia_de_adaptacion_falla_se_adapta_con_reglas(client, con_plan, monkeypatch):
    def falla(*_):
        raise ia_vision.ErrorIA("La IA tardó más de 8 segundos.")

    monkeypatch.setitem(plan_ia.PROVEEDORES_ADAPTACION, "simulada", falla)
    h = con_plan()
    nuevo_gym(client, h)
    s = hoy(client, h)["sesion"]
    assert s["origen"] == "reglas" and s["ejercicios"]


# ---------------- PG-49: fotos ----------------
def test_limite_diario_de_fotos_con_ia(client, gym, cfg, db):
    cfg(ia_limite_fotos_dia=2)
    h, gid = gym()
    ids = [client.post(f"/api/gyms/{gid}/fotos", files={"archivo": ("m.jpg", imagen((i * 40, 90, 90)), "image/jpeg")}, headers=h).json()["id"]
           for i in range(3)]
    assert client.post(f"/api/fotos/{ids[0]}/reconocer", headers=h).status_code == 200
    assert client.post(f"/api/fotos/{ids[1]}/reconocer", headers=h).status_code == 200
    r = client.post(f"/api/fotos/{ids[2]}/reconocer", headers=h)
    assert r.status_code == 429 and r.json()["codigo"] == "limite_ia" and "a mano" in r.json()["detail"]
    # Elegir a mano sigue funcionando.
    assert client.post(f"/api/fotos/{ids[2]}/confirmar", json={"codigo": "PRENSA_45", "origen": "manual"}, headers=h).status_code == 200
    db.expire_all()
    assert db.query(LlamadaIA).filter_by(tipo="foto").count() == 2
    uso = {t["tipo"]: t for t in client.get("/api/ia/uso", headers=h).json()["tipos"]}
    assert uso["foto"] == {"tipo": "foto", "usadas": 2, "limite": 2}


def test_cada_reconocimiento_queda_registrado_aunque_falle(client, gym, db, monkeypatch):
    def falla(*_):
        raise ia_vision.ErrorIA("La IA tardó más de 15 segundos.")

    monkeypatch.setitem(ia_vision.PROVEEDORES, "simulada", falla)
    h, gid = gym()
    fid = client.post(f"/api/gyms/{gid}/fotos", files={"archivo": ("m.jpg", imagen(), "image/jpeg")}, headers=h).json()["id"]
    assert client.post(f"/api/fotos/{fid}/reconocer", headers=h).status_code == 503
    db.expire_all()
    llamada = db.query(LlamadaIA).filter_by(tipo="foto").one()
    assert llamada.resultado == "error" and "15 segundos" in llamada.detalle


def test_los_reemplazos_del_catalogo_nunca_son_de_otra_maquina_inactiva(client, con_plan, db):
    """Una máquina desactivada en el catálogo no habilita ejercicios aunque siga en el inventario."""
    h = con_plan()
    dia = plan_de_hoy(client, h)
    gym_completo(client, h, db, dia)
    con_maquina = next((e for e in dia["ejercicios"] if e["ejercicio"]["categoria_equipo"] == "maquina"), None)
    if con_maquina is None:
        pytest.skip("el día no usa máquinas guiadas")
    ej = db.query(Ejercicio).filter_by(codigo=con_maquina["ejercicio"]["codigo"]).one()
    for x in ej.maquinas:
        db.get(MaquinaCatalogo, x.maquina_id).activa = False
    db.commit()
    s = hoy(client, h)["sesion"]
    assert ej.codigo not in {e["ejercicio"]["codigo"] for e in s["ejercicios"]}
