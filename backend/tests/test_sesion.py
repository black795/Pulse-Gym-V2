"""Sprint 4, sesión en vivo: PG-30 (congelar), PG-34/35 (cronómetro y series), PG-40 (récords), PG-29 (máquina
ocupada), PG-22 (me molesta) y PG-37 (finalizar y calificar)."""
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.db.base import ahora
from app.db.session import SessionLocal
from app.models import Ejercicio, SesionEntreno
from app.services import catalogo_service, lesion_service, sesion_service
from tests.test_hoy import HOY, cfg, con_plan, gym_completo, nuevo_gym, plan_de_hoy  # noqa: F401  (fixtures)


def iniciar(client, h, esperado=201, **datos):
    r = client.post("/api/sesiones", json={"fecha": ahora().date().isoformat(), **datos}, headers=h)
    assert r.status_code == esperado, r.text
    return r.json()


def serie(client, h, s, se, numero, peso=40, reps=10, esperado=200):
    r = client.put(f"/api/sesiones/{s['id']}/ejercicios/{se['id']}/series/{numero}",
                   json={"peso_kg": peso, "repeticiones": reps}, headers=h)
    assert r.status_code == esperado, r.text
    return r.json()


def todas_las_series(client, h, s):
    for e in s["ejercicios"]:
        for n in range(1, e["series"] + 1):
            s = serie(client, h, s, e, n)
    return s


def atrasar(db, sesion_id, minutos):
    """Simula que la sesión empezó hace `minutos`."""
    s = db.get(SesionEntreno, sesion_id)
    s.inicio_at = ahora() - timedelta(minutes=minutos)
    for e in s.ejercicios:
        for x in e.series_hechas:
            x.completada_at = s.inicio_at + timedelta(seconds=x.numero_serie)
    db.commit()


def con_maquina(db, s):
    """Un ejercicio de la sesión que se hace en una máquina o con equipo del gym."""
    return next(e for e in s["ejercicios"] if db.query(Ejercicio).filter_by(id=e["ejercicio"]["id"]).one().maquinas)


# ---------------- PG-30: iniciar y congelar ----------------
def test_sin_plan_no_se_puede_iniciar(client, registrar):
    r = client.post("/api/sesiones", json={}, headers=registrar())
    assert r.status_code == 400 and r.json()["codigo"] == "sin_plan"


def test_iniciar_copia_la_sesion_de_hoy_y_solo_una_a_la_vez(client, con_plan, db):
    h = con_plan()
    gid = gym_completo(client, h, db, plan_de_hoy(client, h))
    hoy = client.get("/api/hoy", params={"fecha": ahora().date().isoformat()}, headers=h).json()
    assert hoy["sesion_en_curso_id"] is None

    s = iniciar(client, h)
    assert s["estado"] == "en_curso" and s["gym_id"] == gid and s["dia"] == HOY and s["resumen"] is None
    assert [e["ejercicio"]["codigo"] for e in s["ejercicios"]] == [e["ejercicio"]["codigo"] for e in hoy["sesion"]["ejercicios"]]
    assert all(e["motivo"] == "plan_original" and e["hechas"] == [] for e in s["ejercicios"])
    assert s["series_planeadas"] == sum(e["series"] for e in s["ejercicios"]) and s["series_hechas"] == 0
    assert s["duracion_estimada_seg"] == hoy["sesion"]["minutos_estimados"] * 60
    assert s["ahora"] >= s["inicio_at"]  # PG-34: el cronómetro se calcula con la hora del servidor

    r = client.post("/api/sesiones", json={}, headers=h)
    assert r.status_code == 409 and r.json()["codigo"] == "sesion_en_curso"
    assert client.get("/api/sesiones/actual", headers=h).json()["id"] == s["id"]
    assert client.get("/api/hoy", params={"fecha": ahora().date().isoformat()}, headers=h).json()["sesion_en_curso_id"] == s["id"]


def test_la_sesion_queda_congelada_aunque_cambie_el_plan_o_el_gym(client, con_plan, db):
    h = con_plan()
    gid = gym_completo(client, h, db, plan_de_hoy(client, h))
    s = iniciar(client, h)
    antes = [(e["ejercicio"]["codigo"], e["series"]) for e in s["ejercicios"]]

    assert client.post("/api/plan", json={"dias": [HOY]}, headers=h).status_code == 201  # plan nuevo
    detalle = client.get(f"/api/gyms/{gid}", headers=h).json()
    for gm in detalle["inventario"]:  # todas las máquinas se malogran
        client.patch(f"/api/gyms/{gid}/maquinas/{gm['id']}", json={"estado": "malograda"}, headers=h)

    despues = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    assert [(e["ejercicio"]["codigo"], e["series"]) for e in despues["ejercicios"]] == antes


def test_adaptacion_al_gym_queda_marcada(client, con_plan):
    h = con_plan()
    nuevo_gym(client, h)  # sin máquinas: todo lo que necesita equipo se cambia por algo sin equipo
    s = iniciar(client, h)
    cambiados = [e for e in s["ejercicios"] if e["reemplaza"]]
    assert cambiados and all(e["motivo"] in ("adaptado_gym", "sin_equipo") and e["nota"] for e in cambiados)


def test_con_varios_gyms_hay_que_elegir(client, con_plan):
    h = con_plan()
    nuevo_gym(client, h, "Gym A")
    gb = nuevo_gym(client, h, "Gym B")
    r = client.post("/api/sesiones", json={}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "elegir_gym"
    assert iniciar(client, h, gym_id=gb)["gym_nombre"] == "Gym B"


def test_descartar_una_sesion_en_curso(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    assert client.delete(f"/api/sesiones/{s['id']}", headers=h).status_code == 204
    assert client.get("/api/sesiones/actual", headers=h).json() is None
    iniciar(client, h)  # se puede volver a empezar


def test_la_sesion_de_otra_persona_no_existe(client, con_plan):
    s = iniciar(client, h := con_plan())
    otra = con_plan(email="luis@pulsegym.app")
    assert client.get(f"/api/sesiones/{s['id']}", headers=otra).status_code == 404
    assert client.post(f"/api/sesiones/{s['id']}/finalizar", headers=otra).status_code == 404
    assert client.get(f"/api/sesiones/{s['id']}", headers=h).status_code == 200


def test_borrar_el_gym_no_borra_la_sesion(client, con_plan):
    h = con_plan()
    gid = nuevo_gym(client, h)
    s = iniciar(client, h)
    assert client.delete(f"/api/gyms/{gid}", headers=h).status_code == 204
    s = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    assert s["gym_id"] is None and s["gym_nombre"] == "Gym Centro"


# ---------------- PG-35: series ----------------
def test_registrar_corregir_y_deshacer_series(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    e = s["ejercicios"][0]
    s = serie(client, h, s, e, 1, peso=40.3, reps=10)
    s = serie(client, h, s, e, 1, peso=40.3, reps=10)  # repetir el pedido no duplica
    hechas = s["ejercicios"][0]["hechas"]
    assert len(hechas) == 1 and hechas[0]["peso_kg"] == 40.5  # de medio en medio kilo
    s = serie(client, h, s, e, 1, peso=42.5, reps=8)  # corregir
    assert s["ejercicios"][0]["hechas"][0]["repeticiones"] == 8 and s["series_hechas"] == 1
    assert s["volumen_kg"] == 42.5 * 8

    s = serie(client, h, s, e, 2, peso=0, reps=12)  # peso 0 = con tu cuerpo
    r = client.delete(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/series/2", headers=h)
    assert r.status_code == 200 and [x["numero"] for x in r.json()["ejercicios"][0]["hechas"]] == [1]
    assert client.delete(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/series/2", headers=h).status_code == 404

    serie(client, h, s, e, e["series"] + 4, esperado=400)  # máximo 3 series extra
    serie(client, h, s, e, 1, reps=0, esperado=422)
    serie(client, h, s, e, 1, peso=-5, esperado=422)
    r = client.put(f"/api/sesiones/{s['id']}/ejercicios/999999/series/1", json={"peso_kg": 1, "repeticiones": 1}, headers=h)
    assert r.status_code == 404


# ---------------- PG-40: récords y "vez pasada" ----------------
def test_records_y_vez_pasada(client, con_plan):
    h = con_plan()
    s1 = iniciar(client, h)
    e1 = s1["ejercicios"][0]
    assert e1["anterior"] == [] and e1["mejor"] is None
    s1 = serie(client, h, s1, e1, 1, peso=50, reps=10)
    s1 = serie(client, h, s1, e1, 2, peso=55, reps=8)
    hechas = s1["ejercicios"][0]["hechas"]
    assert hechas[0]["es_record"] is False  # la primera vez no hay con qué comparar
    assert hechas[1]["es_record"] is True  # superó la serie anterior de la misma sesión
    client.post(f"/api/sesiones/{s1['id']}/finalizar", headers=h)

    s2 = iniciar(client, h)
    e2 = s2["ejercicios"][0]
    assert e2["ejercicio"]["id"] == e1["ejercicio"]["id"]
    assert [(x["numero"], x["peso_kg"], x["repeticiones"]) for x in e2["anterior"]] == [(1, 50, 10), (2, 55, 8)]
    assert e2["mejor"] == {"peso_kg": 55, "repeticiones": 8}
    s2 = serie(client, h, s2, e2, 1, peso=55, reps=8)
    assert s2["ejercicios"][0]["hechas"][0]["es_record"] is False  # igualar no es récord
    s2 = serie(client, h, s2, e2, 2, peso=55, reps=9)
    assert s2["ejercicios"][0]["hechas"][1]["es_record"] is True  # mismo peso, más repeticiones
    s2 = serie(client, h, s2, e2, 2, peso=50, reps=9)  # al corregirla deja de ser récord
    assert s2["ejercicios"][0]["hechas"][1]["es_record"] is False

    s2 = serie(client, h, s2, e2, 3, peso=60, reps=5)
    fin = client.post(f"/api/sesiones/{s2['id']}/finalizar", headers=h).json()
    assert [(r["peso_kg"], r["repeticiones"]) for r in fin["resumen"]["records"]] == [(60, 5)]


# ---------------- PG-29: máquina ocupada ----------------
def test_maquina_ocupada_cambia_solo_hoy(client, con_plan, db):
    h = con_plan()
    gym_completo(client, h, db, plan_de_hoy(client, h))
    s = iniciar(client, h)
    e = con_maquina(db, s)
    ocupadas = {m.maquina.codigo for m in db.query(Ejercicio).filter_by(id=e["ejercicio"]["id"]).one().maquinas}

    r = client.get(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/reemplazos", params={"motivo": "maquina_ocupada"}, headers=h)
    assert r.status_code == 200, r.text
    ops = r.json()["opciones"]
    assert ops, "debe haber al menos un reemplazo (peso libre o sin equipo)"
    en_sesion = {x["ejercicio"]["id"] for x in s["ejercicios"]}
    assert all(o["id"] not in en_sesion for o in ops)
    assert all(not ({m["codigo"] for m in o["maquinas"]} and {m["codigo"] for m in o["maquinas"]} <= ocupadas) for o in ops)
    assert [o["nivel_busqueda"] for o in ops] == sorted(o["nivel_busqueda"] for o in ops)  # máquina → peso libre → sin equipo

    plan_antes = plan_de_hoy(client, h)
    r = client.post(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/reemplazar",
                    json={"ejercicio_id": ops[0]["id"], "motivo": "maquina_ocupada"}, headers=h)
    assert r.status_code == 200, r.text
    nuevo = next(x for x in r.json()["ejercicios"] if x["id"] == e["id"])
    assert nuevo["ejercicio"]["id"] == ops[0]["id"] and nuevo["motivo"] == "maquina_ocupada"
    assert nuevo["reemplaza"]["id"] == e["ejercicio"]["id"] and "plan semanal sigue igual" in nuevo["nota"]
    assert plan_de_hoy(client, h) == plan_antes  # el plan semanal no cambia


def test_reemplazo_fuera_de_la_lista_se_rechaza(client, con_plan, db):
    h = con_plan()
    gym_completo(client, h, db, plan_de_hoy(client, h))
    s = iniciar(client, h)
    e = con_maquina(db, s)
    r = client.post(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/reemplazar",
                    json={"ejercicio_id": e["ejercicio"]["id"], "motivo": "maquina_ocupada"}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "reemplazo_invalido"


def test_reemplazar_despues_de_algunas_series_conserva_lo_hecho(client, con_plan, db):
    h = con_plan()
    gym_completo(client, h, db, plan_de_hoy(client, h))
    s = iniciar(client, h)
    e = con_maquina(db, s)
    s = serie(client, h, s, e, 1)
    ops = client.get(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/reemplazos", params={"motivo": "maquina_ocupada"}, headers=h).json()["opciones"]
    s = client.post(f"/api/sesiones/{s['id']}/ejercicios/{e['id']}/reemplazar",
                    json={"ejercicio_id": ops[0]["id"], "motivo": "maquina_ocupada"}, headers=h).json()
    viejo = next(x for x in s["ejercicios"] if x["id"] == e["id"])
    nuevo = next(x for x in s["ejercicios"] if x["orden"] == viejo["orden"] + 1)
    assert viejo["cerrado"] and viejo["series"] == 1 and len(viejo["hechas"]) == 1
    assert nuevo["ejercicio"]["id"] == ops[0]["id"] and not nuevo["cerrado"]
    assert len({x["orden"] for x in s["ejercicios"]}) == len(s["ejercicios"])  # sin órdenes repetidos
    serie(client, h, s, viejo, 2, esperado=409)  # ya no se registra en el reemplazado
    serie(client, h, s, nuevo, 1)


# ---------------- PG-22: me molesta ----------------
def preparar_reemplazo_por_molestia(client, h, s, zona="hombro"):
    ejercicio = s["ejercicios"][0]
    base = f"/api/sesiones/{s['id']}/ejercicios/{ejercicio['id']}"
    r = client.get(f"{base}/reemplazos", params={"motivo": "molestia_dolor", "zona": zona}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["opciones"]
    datos = {"ejercicio_id": r.json()["opciones"][0]["id"], "motivo": "molestia_dolor", "zona": zona}
    return ejercicio, base, datos


def test_reemplazo_por_molestia_sin_guardar_lesion(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)

    r = client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": False}, headers=h)

    assert r.status_code == 200, r.text
    reemplazo = next(e for e in r.json()["ejercicios"] if e["id"] == ejercicio["id"])
    assert reemplazo["ejercicio"]["id"] == datos["ejercicio_id"]
    assert client.get("/api/lesiones", headers=h).json()["lesiones"] == []


def test_reemplazo_por_molestia_guarda_lesion_y_ejercicio(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)

    r = client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert r.status_code == 200, r.text
    reemplazo = next(e for e in r.json()["ejercicios"] if e["id"] == ejercicio["id"])
    assert reemplazo["ejercicio"]["id"] == datos["ejercicio_id"]
    lesiones = client.get("/api/lesiones", headers=h).json()["lesiones"]
    assert [(lesion["zona"]["codigo"], lesion["estado"]) for lesion in lesiones] == [("hombro", "activa")]
    actual = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    assert next(e for e in actual["ejercicios"] if e["id"] == ejercicio["id"])["ejercicio"]["id"] == datos["ejercicio_id"]


def test_reemplazo_con_lesion_confirma_una_sola_vez(client, con_plan, monkeypatch):
    h = con_plan()
    s = iniciar(client, h)
    _, base, datos = preparar_reemplazo_por_molestia(client, h, s)
    commit_original = Session.commit
    confirmaciones = []

    def contar_commit(db):
        confirmaciones.append(db)
        return commit_original(db)

    with monkeypatch.context() as parche:
        parche.setattr(Session, "commit", contar_commit)
        r = client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert r.status_code == 200, r.text
    assert len(confirmaciones) == 1


def test_reemplazo_no_duplica_lesion_activa_existente(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    creada = client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=h)
    assert creada.status_code == 201, creada.text
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)

    r = client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert r.status_code == 200, r.text
    reemplazo = next(e for e in r.json()["ejercicios"] if e["id"] == ejercicio["id"])
    assert reemplazo["ejercicio"]["id"] == datos["ejercicio_id"]
    lesiones = client.get("/api/lesiones", headers=h).json()["lesiones"]
    assert [lesion["id"] for lesion in lesiones] == [creada.json()["id"]]


def test_reemplazo_no_guarda_lesion_sin_consentimiento(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    r = client.put("/api/consentimiento", json={"acepta": False}, headers=h)
    assert r.status_code == 200, r.text
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)

    r = client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert r.status_code == 403
    assert r.json()["codigo"] == "consentimiento_requerido"
    actual = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    assert next(e for e in actual["ejercicios"] if e["id"] == ejercicio["id"])["ejercicio"]["id"] == ejercicio["ejercicio"]["id"]
    assert client.get("/api/lesiones", headers=h).json()["lesiones"] == []


def test_fallo_despues_de_preparar_lesion_revierte_lesion_y_reemplazo(client, con_plan, monkeypatch):
    h = con_plan()
    s = iniciar(client, h)
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)
    preparar_lesion = lesion_service._preparar_creacion

    def preparar_y_fallar(*args, **kwargs):
        preparar_lesion(*args, **kwargs)  # flush sin commit
        raise RuntimeError("fallo después de preparar la lesión")

    with monkeypatch.context() as parche:
        parche.setattr(lesion_service, "_preparar_creacion", preparar_y_fallar)
        with pytest.raises(RuntimeError, match="fallo después de preparar la lesión"):
            client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    # Ambas lecturas abren una sesión nueva: comprueban lo que realmente quedó confirmado.
    lesiones = client.get("/api/lesiones", headers=h).json()["lesiones"]
    assert lesiones == []
    actual = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    reemplazo = next(e for e in actual["ejercicios"] if e["id"] == ejercicio["id"])
    assert reemplazo["ejercicio"]["id"] == ejercicio["ejercicio"]["id"]
    assert client.get("/api/perfil", headers=h).json()["plan_requiere_regenerar"] is False


def test_fallo_tras_cambiar_ejercicio_revierte_lesion_y_reemplazo(client, con_plan, monkeypatch):
    h = con_plan()
    s = iniciar(client, h)
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)

    def fallar_al_elegir_maquina(*args, **kwargs):
        raise RuntimeError("fallo después de cambiar el ejercicio")

    with monkeypatch.context() as parche:
        parche.setattr(sesion_service, "_gym_maquina_id", fallar_al_elegir_maquina)
        with pytest.raises(RuntimeError, match="fallo después de cambiar el ejercicio"):
            client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert client.get("/api/lesiones", headers=h).json()["lesiones"] == []
    actual = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    reemplazo = next(e for e in actual["ejercicios"] if e["id"] == ejercicio["id"])
    assert reemplazo["ejercicio"]["id"] == ejercicio["ejercicio"]["id"]


def test_fallo_al_confirmar_revierte_lesion_y_reemplazo(client, con_plan, monkeypatch):
    h = con_plan()
    s = iniciar(client, h)
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, s)

    def fallar_al_confirmar(db):
        raise RuntimeError("fallo al confirmar el reemplazo")

    with monkeypatch.context() as parche:
        parche.setattr(Session, "commit", fallar_al_confirmar)
        with pytest.raises(RuntimeError, match="fallo al confirmar el reemplazo"):
            client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert client.get("/api/lesiones", headers=h).json()["lesiones"] == []
    actual = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    reemplazo = next(e for e in actual["ejercicios"] if e["id"] == ejercicio["id"])
    assert reemplazo["ejercicio"]["id"] == ejercicio["ejercicio"]["id"]


def test_crear_lesion_independiente_persiste(client, con_consentimiento):
    h = con_consentimiento()
    r = client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=h)

    assert r.status_code == 201, r.text
    lesiones = client.get("/api/lesiones", headers=h).json()["lesiones"]
    assert [(lesion["id"], lesion["zona"]["codigo"]) for lesion in lesiones] == [(r.json()["id"], "hombro")]


def test_me_molesta_propone_algo_que_no_cargue_esa_zona_y_puede_guardarla(client, con_plan, db):
    h = con_plan()
    s = iniciar(client, h)
    e = s["ejercicios"][0]
    base = f"/api/sesiones/{s['id']}/ejercicios/{e['id']}"
    r = client.get(f"{base}/reemplazos", params={"motivo": "molestia_dolor"}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "falta_zona"

    for zona in ("rodilla", "hombro", "espalda_baja"):
        d = client.get(f"{base}/reemplazos", params={"motivo": "molestia_dolor", "zona": zona}, headers=h).json()
        assert d["puede_guardar_lesion"] is True and "médico" in d["aviso"]
        for o in d["opciones"]:
            assert catalogo_service.revisar_lesiones(db.get(Ejercicio, o["id"]), {zona: "activa"})[0], (zona, o["codigo"])

    d = client.get(f"{base}/reemplazos", params={"motivo": "molestia_dolor", "zona": "hombro"}, headers=h).json()
    assert d["opciones"], "sin gym hay ejercicios sin equipo que no cargan el hombro"
    r = client.post(f"{base}/reemplazar", json={"ejercicio_id": d["opciones"][0]["id"], "motivo": "molestia_dolor",
                                                "zona": "hombro", "guardar_lesion": True}, headers=h)
    assert r.status_code == 200, r.text
    assert next(x for x in r.json()["ejercicios"] if x["id"] == e["id"])["motivo"] == "molestia_dolor"
    lesiones = client.get("/api/lesiones", headers=h).json()["lesiones"]
    assert any(l["zona"]["codigo"] == "hombro" and l["estado"] == "activa" for l in lesiones)


def test_zona_inexistente(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    r = client.get(f"/api/sesiones/{s['id']}/ejercicios/{s['ejercicios'][0]['id']}/reemplazos",
                   params={"motivo": "molestia_dolor", "zona": "oreja"}, headers=h)
    assert r.status_code == 400


# ---------------- PG-37: finalizar y calificar ----------------
def test_sesion_sin_series_es_parcial(client, con_plan):
    h = con_plan()
    s = iniciar(client, h)
    fin = client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h).json()
    assert fin["estado"] == "parcial" and fin["resumen"]["cuenta_asistencia"] is False
    assert fin["resumen"]["series_hechas"] == 0 and "historial" in fin["resumen"]["mensaje"]
    assert client.get("/api/sesiones/actual", headers=h).json() is None


def test_sesion_completa_con_tiempo_coherente(client, con_plan, db):
    h = con_plan()
    s = todas_las_series(client, h, iniciar(client, h))
    atrasar(db, s["id"], s["duracion_estimada_seg"] // 60)
    fin = client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h).json()
    r = fin["resumen"]
    assert fin["estado"] == "completa" and r["cuenta_asistencia"] is True and r["porcentaje"] == 100
    assert r["series_hechas"] == r["series_planeadas"] and r["duracion_seg"] >= s["duracion_estimada_seg"] - 60
    assert "completa" in r["mensaje"]

    again = client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h).json()  # dos veces: no cambia nada
    assert again["fin_at"] == fin["fin_at"]
    serie(client, h, s, s["ejercicios"][0], 1, esperado=409)


def test_todas_las_series_en_muy_poco_tiempo_es_parcial(client, con_plan):
    h = con_plan()
    s = todas_las_series(client, h, iniciar(client, h))
    fin = client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h).json()
    assert fin["estado"] == "parcial" and fin["resumen"]["porcentaje"] == 100


def test_ochenta_por_ciento_alcanza(client, con_plan, db):
    h = con_plan()
    s = iniciar(client, h)
    objetivo = -(-s["series_planeadas"] * 8 // 10)  # 80 % redondeado hacia arriba
    hechas = 0
    for e in s["ejercicios"]:
        for n in range(1, e["series"] + 1):
            if hechas < objetivo:
                s = serie(client, h, s, e, n)
                hechas += 1
    atrasar(db, s["id"], s["duracion_estimada_seg"] // 60)
    assert client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h).json()["estado"] == "completa"


def test_sesion_olvidada_se_cierra_sola(client, con_plan, db):
    h = con_plan()
    s = iniciar(client, h)
    serie(client, h, s, s["ejercicios"][0], 1)
    atrasar(db, s["id"], 7 * 60)
    assert client.get("/api/sesiones/actual", headers=h).json() is None
    viejo = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    assert viejo["estado"] == "parcial" and viejo["cerrada_auto"] and "abierta" in viejo["resumen"]["mensaje"]
    iniciar(client, h)  # ya se puede empezar otra


@pytest.mark.parametrize("con_sesion", [False, True], ids=["sin-sesion", "sesion-reciente"])
def test_consulta_actual_sin_sesiones_vencidas_no_confirma(client, con_plan, monkeypatch, con_sesion):
    h = con_plan()
    sesion = iniciar(client, h) if con_sesion else None
    confirmaciones = []
    commit_original = Session.commit

    def contar_commit(db):
        confirmaciones.append(1)
        return commit_original(db)

    with monkeypatch.context() as parche:
        parche.setattr(Session, "commit", contar_commit)
        respuesta = client.get("/api/sesiones/actual", headers=h)

    assert respuesta.status_code == 200
    if sesion is None:
        assert respuesta.json() is None
    else:
        assert respuesta.json()["id"] == sesion["id"]
        assert respuesta.json()["estado"] == "en_curso"
        assert respuesta.json()["cerrada_auto"] is False
    assert confirmaciones == []


def test_cierre_automatico_completo_persiste_con_ultima_serie(client, con_plan, db):
    h = con_plan()
    sesion = todas_las_series(client, h, iniciar(client, h))
    fila = db.get(SesionEntreno, sesion["id"])
    inicio = ahora() - timedelta(hours=7)
    ultima = inicio + timedelta(hours=1)
    fila.inicio_at = inicio
    for ejercicio in fila.ejercicios:
        for registrada in ejercicio.series_hechas:
            registrada.completada_at = ultima
    db.commit()

    respuesta = client.get("/api/sesiones/actual", headers=h)

    assert respuesta.status_code == 200 and respuesta.json() is None
    with SessionLocal() as nueva:
        guardada = nueva.get(SesionEntreno, sesion["id"])
        assert guardada.estado == "completa"
        assert guardada.cerrada_auto is True
        assert guardada.cuenta_asistencia is True
        assert guardada.fin_at == ultima


def test_cierre_automatico_no_modifica_sesiones_de_otro_usuario(client, con_plan, db):
    primera = con_plan()
    segunda = con_plan(email="segundo@pulsegym.app")
    sesion_primera = iniciar(client, primera)
    sesion_segunda = iniciar(client, segunda)
    atrasar(db, sesion_primera["id"], 7 * 60)
    atrasar(db, sesion_segunda["id"], 7 * 60)

    respuesta = client.get("/api/sesiones/actual", headers=primera)

    assert respuesta.status_code == 200 and respuesta.json() is None
    with SessionLocal() as nueva:
        propia = nueva.get(SesionEntreno, sesion_primera["id"])
        otra = nueva.get(SesionEntreno, sesion_segunda["id"])
        assert (propia.estado, propia.cerrada_auto, propia.cuenta_asistencia) == ("parcial", True, False)
        assert (otra.estado, otra.cerrada_auto, otra.cuenta_asistencia) == ("en_curso", False, False)
        assert otra.fin_at is None


def test_reemplazo_con_lesion_en_sesion_vencida_cierra_sin_crear_lesion(client, con_plan, db, monkeypatch):
    h = con_plan()
    sesion = iniciar(client, h)
    ejercicio, base, datos = preparar_reemplazo_por_molestia(client, h, sesion)
    atrasar(db, sesion["id"], 7 * 60)
    preparaciones = []
    monkeypatch.setattr(lesion_service, "_preparar_creacion", lambda *args: preparaciones.append(args))

    respuesta = client.post(f"{base}/reemplazar", json={**datos, "guardar_lesion": True}, headers=h)

    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "sesion_terminada"
    assert preparaciones == []
    assert client.get("/api/lesiones", headers=h).json()["lesiones"] == []
    with SessionLocal() as nueva:
        guardada = nueva.get(SesionEntreno, sesion["id"])
        assert (guardada.estado, guardada.cerrada_auto, guardada.cuenta_asistencia) == ("parcial", True, False)
        assert next(e for e in guardada.ejercicios if e.id == ejercicio["id"]).ejercicio_id == ejercicio["ejercicio"]["id"]
