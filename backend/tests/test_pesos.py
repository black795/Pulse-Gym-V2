"""Sprint 5: historial de máquinas y pesos, peso sugerido (IA la primera vez, historial después), alertas PG-42/PG-43
y PG-39 (olvidé marcar series / registrar entrenamiento pasado)."""
from datetime import datetime, time, timedelta

from app.db.base import ahora
from app.models import Ejercicio, Rutina, SerieRegistrada, SesionEjercicio, SesionEntreno
from app.services import plan_ia, progresion
from tests.test_hoy import HOY, con_plan, gym_completo, hoy, plan_de_hoy  # noqa: F401  (fixtures)
from tests.test_plan import _valido, generar, ia_plan, usuario_listo  # noqa: F401  (fixtures)
from tests.test_sesion import iniciar, serie

FECHA = ahora().date()


def mi_id(client, h):
    return client.get("/api/auth/me", headers=h).json()["id"]


def una_maquina(db, multiarticular=True) -> Ejercicio:
    return db.query(Ejercicio).filter_by(categoria_equipo="maquina", multiarticular=multiarticular).order_by(Ejercicio.id).first()


def hecha(db, usuario_id, ejercicio, dias_atras, series, plan=3, reps=(8, 10), estado="completa"):
    """Una sesión terminada hace `dias_atras` días con las series (peso, reps) de un ejercicio."""
    fecha = FECHA - timedelta(days=dias_atras)
    inicio = datetime.combine(fecha, time(12))
    s = SesionEntreno(usuario_id=usuario_id, dia_semana="lunes", enfoque="Cuerpo completo A", fecha=fecha,
                      inicio_at=inicio, fin_at=inicio + timedelta(minutes=50), estado=estado,
                      cuenta_asistencia=estado == "completa", gym_nombre="Gym Centro")
    se = SesionEjercicio(ejercicio_id=ejercicio.id, orden=1, series=plan, reps_min=reps[0], reps_max=reps[1], descanso_seg=90)
    se.series_hechas = [SerieRegistrada(numero_serie=n, peso_kg=p, repeticiones=r, completada_at=inicio)
                        for n, (p, r) in enumerate(series, start=1)]
    s.ejercicios.append(se)
    db.add(s)
    db.commit()
    return s


def usados(client, h):
    r = client.get("/api/progreso/ejercicios", params={"fecha": FECHA.isoformat()}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["ejercicios"]


def alertas(client, h):
    return client.get("/api/progreso/alertas", params={"fecha": FECHA.isoformat()}, headers=h).json()["alertas"]


# ---------------- Historial de máquinas ----------------
def test_exige_sesion_iniciada(client):
    for ruta in ("/api/progreso/ejercicios", "/api/progreso/ejercicios/1", "/api/progreso/alertas"):
        assert client.get(ruta).status_code == 401


def test_solo_aparecen_las_maquinas_que_ya_usaste(client, registrar, db):
    ana, beto = registrar("ana@x.com"), registrar("beto@x.com", nombre="Beto Díaz")
    assert usados(client, ana) == []
    prensa, otra = una_maquina(db), una_maquina(db, multiarticular=False)
    hecha(db, mi_id(client, ana), prensa, 10, [(40, 10), (40, 9)])
    hecha(db, mi_id(client, ana), prensa, 3, [(45, 10), (45, 8)])

    lista = usados(client, ana)
    assert [e["ejercicio"]["id"] for e in lista] == [prensa.id]  # `otra` nunca la usó: no aparece
    p = lista[0]
    assert p["veces"] == 2 and p["peso_inicial_kg"] == 40 and p["peso_actual_kg"] == 45
    assert p["mejor"] == {"peso_kg": 45, "repeticiones": 10}
    assert [m["peso_kg"] for m in p["ultima"]] == [45, 45]
    assert p["sugerencia"]["origen"] == "historial"
    assert p["ejercicio"]["maquinas"]  # el nombre de la máquina, para mostrarlo

    assert usados(client, beto) == []  # el historial es de cada persona
    assert client.get(f"/api/progreso/ejercicios/{prensa.id}", headers=beto).status_code == 404
    assert client.get(f"/api/progreso/ejercicios/{otra.id}", headers=ana).status_code == 404


def test_detalle_con_la_evolucion_de_la_mas_antigua_a_la_mas_reciente(client, registrar, db):
    h = registrar()
    prensa = una_maquina(db)
    for atras, peso in ((20, 40), (10, 42.5), (2, 45)):
        hecha(db, mi_id(client, h), prensa, atras, [(peso, 10), (peso - 5, 12)])
    d = client.get(f"/api/progreso/ejercicios/{prensa.id}", params={"fecha": FECHA.isoformat()}, headers=h).json()
    assert [v["peso_max_kg"] for v in d["historial"]] == [40, 42.5, 45]
    ultimo = d["historial"][-1]
    assert ultimo["reps_con_peso_max"] == 10 and ultimo["volumen_kg"] == 45 * 10 + 40 * 12
    assert [s["numero"] for s in ultimo["series"]] == [1, 2] and d["estancamiento"] is None


def test_la_sugerencia_sube_si_completaste_todo_y_baja_si_volviste_tras_una_ausencia(client, registrar, db):
    h = registrar()
    prensa, curl = una_maquina(db), una_maquina(db, multiarticular=False)
    hecha(db, mi_id(client, h), prensa, 3, [(40, 10)] * 3)
    hecha(db, mi_id(client, h), curl, 20, [(20, 10)] * 3)
    por_id = {e["ejercicio"]["id"]: e["sugerencia"] for e in usados(client, h)}
    assert (por_id[prensa.id]["tipo"], por_id[prensa.id]["peso_kg"]) == ("subir", 42.5)
    assert (por_id[curl.id]["tipo"], por_id[curl.id]["peso_kg"]) == ("retorno", 18)


def test_alerta_de_retorno_y_de_estancamiento(client, registrar, db):
    h = registrar()
    remo = una_maquina(db)
    for atras in (16, 23, 30):
        hecha(db, mi_id(client, h), remo, atras, [(40, 8)] * 3)
    tipos = [a["tipo"] for a in alertas(client, h)]
    assert tipos == ["retorno"]  # tras 2 semanas sin entrenar no se habla de estancamiento

    h2 = registrar("beto@x.com", nombre="Beto Díaz")
    for atras in (1, 8, 15):
        hecha(db, mi_id(client, h2), remo, atras, [(40, 8)] * 3)
    a = alertas(client, h2)
    assert [x["tipo"] for x in a] == ["estancamiento"] and a[0]["ejercicio_id"] == remo.id
    assert "40 kg" in a[0]["titulo"]
    d = client.get(f"/api/progreso/ejercicios/{remo.id}", params={"fecha": FECHA.isoformat()}, headers=h2).json()
    assert d["estancamiento"]["tipo"] == "estancamiento"


# ---------------- La IA da los pesos iniciales; después manda el historial ----------------
def _pesos_plan(plan):
    return {e["ejercicio"]["id"]: (e["ejercicio"]["categoria_equipo"], e["peso_sugerido"])
            for d in plan["dias"] for e in d["ejercicios"]}


def test_la_primera_vez_la_ia_estima_los_pesos_dentro_de_un_margen(client, usuario_listo, ia_plan, db):
    h = usuario_listo()
    base = _pesos_plan(generar(client, h, ["lunes", "jueves"])["plan"])
    for categoria, sug in base.values():
        if categoria == "sin_equipo":
            assert sug is None  # con tu cuerpo: no hay peso que sugerir
        else:
            assert sug["tipo"] == "inicial" and sug["origen"] == "ia" and sug["peso_kg"] > 0

    def exagerada(ctx, pedido, _l):  # la IA propone 900 kg para todo
        datos = _valido(ctx, pedido)[1]
        for e in datos.get("ejercicios", []):
            e["peso_kg"] = 900
        return "modelo-prueba", datos

    ia_plan(exagerada)
    plan = generar(client, h, ["lunes", "jueves"])["plan"]
    for eid, (categoria, sug) in _pesos_plan(plan).items():
        if categoria != "sin_equipo":  # las reglas la acotan a 1,5 veces su estimación
            assert sug["peso_kg"] == progresion.redondear(base[eid][1]["peso_kg"] * 1.5), eid
    rutina = db.query(Rutina).filter_by(estado="activa").one()
    assert rutina.parametros["pesos_base"] and all(v["origen"] == "ia" for v in rutina.parametros["pesos_base"].values())


def test_si_la_ia_no_manda_pesos_se_usan_los_de_reglas(client, usuario_listo, ia_plan):
    def sin_pesos(ctx, pedido, _l):
        datos = _valido(ctx, pedido)[1]
        for e in datos.get("ejercicios", []):
            e.pop("peso_kg", None)
        return "modelo-prueba", datos

    ia_plan(sin_pesos)
    plan = generar(client, usuario_listo(), ["lunes", "jueves"])["plan"]
    sugeridos = [s for c, s in _pesos_plan(plan).values() if c != "sin_equipo"]
    assert sugeridos and all(s["origen"] == "reglas" for s in sugeridos)


def test_el_prompt_pide_peso_y_muestra_los_pesos_que_ya_usa(client, usuario_listo, ia_plan, db):
    vistos = []

    def espia(ctx, pedido, _l):
        if pedido.tipo == "dia":
            vistos.append((plan_ia.prompt_dia(ctx, pedido), plan_ia.esquema_dia(ctx, pedido.dia)))
        return _valido(ctx, pedido)

    h = usuario_listo()
    hecha(db, mi_id(client, h), una_maquina(db), 3, [(55, 10)])
    ia_plan(espia)
    generar(client, h, ["lunes", "jueves"])
    prompt, esquema = vistos[0]
    assert "55 kg × 10" in prompt and "peso_kg" in prompt
    assert "peso_kg" in esquema["properties"]["ejercicios"]["items"]["required"]


def test_hoy_y_la_sesion_usan_el_historial_para_subir_el_peso(client, con_plan, db):
    h = con_plan()
    gym_completo(client, h, db, plan_de_hoy(client, h))
    ejercicios = hoy(client, h)["sesion"]["ejercicios"]
    con_peso = [e for e in ejercicios if e["ejercicio"]["categoria_equipo"] != "sin_equipo"]
    assert con_peso and all(e["peso_sugerido"]["tipo"] == "inicial" for e in con_peso)

    s = iniciar(client, h)
    assert all(e["sugerencia"]["tipo"] == "inicial" for e in s["ejercicios"] if e["ejercicio"]["categoria_equipo"] != "sin_equipo")
    for e in s["ejercicios"]:  # todas las series al tope del rango con 40 kg
        for n in range(1, e["series"] + 1):
            s = serie(client, h, s, e, n, peso=40, reps=e["reps_max"])
    client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h)

    s2 = iniciar(client, h)
    for e in s2["ejercicios"]:
        multi = db.get(Ejercicio, e["ejercicio"]["id"]).multiarticular
        assert e["sugerencia"]["tipo"] == "subir" and e["sugerencia"]["origen"] == "historial"
        assert e["sugerencia"]["peso_kg"] == 40 + progresion.incremento(40, multi)
    terminada = client.get(f"/api/sesiones/{s['id']}", headers=h).json()
    assert all(e["sugerencia"] is None for e in terminada["ejercicios"])  # solo mientras entrenas


# ---------------- PG-39: olvidé marcar series ----------------
def test_completar_una_sesion_parcial_con_lo_planeado(client, con_plan, db):
    h = con_plan()
    s = iniciar(client, h)
    e1 = s["ejercicios"][0]
    s = serie(client, h, s, e1, 1, peso=50, reps=10)
    fin = client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h).json()
    assert fin["estado"] == "parcial" and fin["resumen"]["cuenta_asistencia"] is False

    r = client.post(f"/api/sesiones/{s['id']}/completar", headers=h)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["estado"] == "manual" and c["resumen"]["estado"] == "manual" and c["resumen"]["cuenta_asistencia"] is True
    assert c["series_hechas"] == c["series_planeadas"]
    primero = c["ejercicios"][0]
    agregadas = [x for x in primero["hechas"] if x["numero"] > 1]
    assert all(x["peso_kg"] == 50 and x["repeticiones"] == e1["reps_min"] for x in agregadas)
    assert not any(x["es_record"] for e in c["ejercicios"] for x in e["hechas"][1:] if e["id"] == primero["id"])
    assert not any(x["es_record"] for e in c["ejercicios"][1:] for x in e["hechas"])  # lo agregado no es récord

    otra = client.post(f"/api/sesiones/{s['id']}/completar", headers=h)
    assert otra.status_code == 409 and otra.json()["codigo"] == "no_parcial"


def test_completar_tiene_plazo(client, con_plan, db):
    h = con_plan()
    s = iniciar(client, h)
    client.post(f"/api/sesiones/{s['id']}/finalizar", headers=h)
    sesion = db.get(SesionEntreno, s["id"])
    sesion.fin_at = ahora() - timedelta(hours=49)
    db.commit()
    r = client.post(f"/api/sesiones/{s['id']}/completar", headers=h)
    assert r.status_code == 409 and r.json()["codigo"] == "fuera_de_plazo"


# ---------------- PG-39: registrar entrenamiento pasado ----------------
def pasada(client, h, esperado=201, **datos):
    r = client.post("/api/sesiones/pasadas", json=datos, headers=h)
    assert r.status_code == esperado, r.text
    return r.json()


def test_registrar_un_entrenamiento_pasado(client, con_plan, db):
    h = con_plan()
    gid = gym_completo(client, h, db, plan_de_hoy(client, h))
    dia = hoy(client, h, gym_id=gid)["sesion"]
    ayer = (FECHA - timedelta(days=1)).isoformat()
    primero = dia["ejercicios"][0]
    s = pasada(client, h, fecha=ayer, dia=HOY, gym_id=gid,
               ejercicios=[{"ejercicio_id": primero["ejercicio"]["id"], "series": [{"peso_kg": 40.3, "repeticiones": 10}] * 2}])
    assert s["estado"] == "manual" and s["fecha"] == ayer and s["gym_id"] == gid
    assert s["series_hechas"] == 2 and s["resumen"]["cuenta_asistencia"] is False  # 2 series no llegan al 80 %
    assert [x["peso_kg"] for x in s["ejercicios"][0]["hechas"]] == [40.5, 40.5]  # de medio en medio kilo

    repetida = client.post("/api/sesiones/pasadas", json={"fecha": ayer, "dia": HOY, "gym_id": gid, "ejercicios": [
        {"ejercicio_id": primero["ejercicio"]["id"], "series": [{"peso_kg": 40, "repeticiones": 10}]}]}, headers=h)
    assert repetida.status_code == 409 and repetida.json()["codigo"] == "ya_registrada"

    historial = client.get("/api/progreso/historial", headers=h).json()["sesiones"]
    assert historial[0]["estado"] == "manual"
    assert primero["ejercicio"]["id"] in [e["ejercicio"]["id"] for e in usados(client, h)]


def test_un_pasado_completo_cuenta_para_la_constancia(client, con_plan, db):
    h = con_plan()
    gid = gym_completo(client, h, db, plan_de_hoy(client, h))
    dia = hoy(client, h, gym_id=gid)["sesion"]
    hace2 = FECHA - timedelta(days=2)
    s = pasada(client, h, fecha=hace2.isoformat(), dia=HOY, gym_id=gid, ejercicios=[
        {"ejercicio_id": e["ejercicio"]["id"], "series": [{"peso_kg": 30, "repeticiones": e["reps_max"]}] * e["series"]}
        for e in dia["ejercicios"]])
    assert s["resumen"]["cuenta_asistencia"] is True and s["resumen"]["porcentaje"] == 100
    c = client.get("/api/progreso/constancia", params={"fecha": hace2.isoformat()}, headers=h).json()
    assert c["entreno_hoy"] is True


def test_registrar_pasado_valida_fecha_ejercicios_y_series(client, con_plan, db):
    h = con_plan()
    gid = gym_completo(client, h, db, plan_de_hoy(client, h))
    del_dia = [e["ejercicio"]["id"] for e in hoy(client, h, gym_id=gid)["sesion"]["ejercicios"]]
    eid = del_dia[0]
    ayer = (FECHA - timedelta(days=1)).isoformat()
    una = [{"peso_kg": 20, "repeticiones": 10}]

    r = client.post("/api/sesiones/pasadas", json={"fecha": (FECHA - timedelta(days=10)).isoformat(), "dia": HOY,
                                                   "gym_id": gid, "ejercicios": [{"ejercicio_id": eid, "series": una}]}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "fecha_invalida"
    ajeno = db.query(Ejercicio).filter(Ejercicio.id.notin_(del_dia)).first().id
    r = client.post("/api/sesiones/pasadas", json={"fecha": ayer, "dia": HOY, "gym_id": gid,
                                                   "ejercicios": [{"ejercicio_id": ajeno, "series": una}]}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "ejercicio_invalido"
    r = client.post("/api/sesiones/pasadas", json={"fecha": ayer, "dia": HOY, "gym_id": gid,
                                                   "ejercicios": [{"ejercicio_id": eid, "series": []}]}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "sin_series"
    r = client.post("/api/sesiones/pasadas", json={"fecha": ayer, "dia": HOY, "gym_id": gid,
                                                   "ejercicios": [{"ejercicio_id": eid, "series": [{"peso_kg": 900, "repeticiones": 10}]}]}, headers=h)
    assert r.status_code == 422
    assert db.query(SesionEntreno).count() == 0  # nada quedó a medias
