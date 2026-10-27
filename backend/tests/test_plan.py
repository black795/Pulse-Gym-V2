"""PG-20 (lesiones), PG-23 (plan), PG-24 (días), PG-25 (series y descanso), PG-26 (validación de la IA),
PG-27 (explicación) y PG-49 (límites y costo de la IA, parte del plan)."""
import itertools
import threading
import time

import pytest

from app.core.config import get_settings
from app.models import Ejercicio, EjercicioContraindicacion, GrupoMuscular, LlamadaIA, ZonaLesion
from app.models.plan import DIAS_SEMANA
from app.services import ia_cliente, ia_uso_service, plan_ia
from app.services import plan_reglas as reglas
from app.services.ia_cliente import ErrorIA


@pytest.fixture()
def cfg(monkeypatch):
    """cfg(x=1) cambia la configuración solo durante la prueba."""
    ia_uso_service._alerta_enviada = None

    def _fijar(**valores):
        for k, v in valores.items():
            monkeypatch.setattr(get_settings(), k, v)

    return _fijar


@pytest.fixture()
def usuario_listo(client, con_consentimiento):
    """Cuenta con consentimiento y perfil completo para armar el plan."""

    def _crear(email="ana@pulsegym.app", **perfil) -> dict:
        h = con_consentimiento(email)
        datos = {"objetivo": "ganar_musculo", "nivel": "intermedio", "dias_por_semana": 3, "minutos_por_sesion": 60,
                 "edad": 30, "sexo": "femenino", "peso_kg": 62, "grasa_pct": 24, "masa_muscular_kg": 26, **perfil}
        assert client.put("/api/perfil", json=datos, headers=h).status_code == 200
        return h

    return _crear


@pytest.fixture()
def ia_plan(monkeypatch):
    """ia_plan(f) → la IA del plan responde cada pedido (general o un día) con f(ctx, pedido, limite).
    f puede lanzar ErrorIA."""

    def _fijar(funcion):
        monkeypatch.setitem(plan_ia.PROVEEDORES_PLAN, "simulada", funcion)

    return _fijar


def generar(client, h, dias=None, esperado=201):
    r = client.post("/api/plan", json={"dias": dias} if dias else {}, headers=h)
    assert r.status_code == esperado, r.text
    return r.json()


def codigos_plan(plan) -> list[str]:
    return [e["ejercicio"]["codigo"] for d in plan["dias"] for e in d["ejercicios"]]


def contraindicados(db, zona: str, niveles=("evitar", "precaucion")) -> set[str]:
    return {
        e.codigo for e in db.query(Ejercicio).join(EjercicioContraindicacion).join(ZonaLesion)
        .filter(ZonaLesion.codigo == zona, EjercicioContraindicacion.nivel.in_(niveles))
    }


def grupos_por_codigo(db) -> dict[str, str]:
    return {e.codigo: e.musculo_principal.codigo for e in db.query(Ejercicio) if e.musculo_principal}


def ctx_ficticio(dias, **kw) -> reglas.Contexto:
    """Contexto de reglas sin base de datos: 3 ejercicios por grupo, sin lesiones."""
    permitidos = {}
    for g in ["pecho", "espalda", "hombros", "biceps", "triceps", "cuadriceps", "isquiotibiales", "gluteos", "pantorrillas", "core"]:
        for i in range(3):
            c = f"{g.upper()}_{i}"
            permitidos[c] = reglas.EjercicioInfo(i, c, c.title(), g, i == 0, "media", "maquina")
    base = dict(dias=dias, objetivo="ganar_musculo", objetivo_tipo="musculo", nivel="intermedio", minutos=60,
                permitidos=permitidos, bloqueados={}, nombres_grupos={}, zonas={}, nombres_zonas={})
    return reglas.preparar(reglas.Contexto(**{**base, **kw}))


# ---------------- PG-23 ----------------
def test_sin_perfil_completo_no_se_arma_el_plan(client, registrar):
    h = registrar()
    estado = client.get("/api/plan", headers=h).json()
    assert estado["plan"] is None and not estado["puede_generar"] and "objetivo" in estado["faltan"]
    r = client.post("/api/plan", json={}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "perfil_incompleto"


def test_el_plan_tiene_exactamente_los_dias_elegidos_con_un_enfoque_cada_uno(client, usuario_listo, db):
    h = usuario_listo()
    assert client.get("/api/plan", headers=h).json()["dias_sugeridos"] == ["lunes", "miercoles", "viernes"]
    inicio = time.perf_counter()
    estado = generar(client, h, ["viernes", "martes", "jueves", "sabado"])
    assert time.perf_counter() - inicio < 20  # PG-23: menos de 20 segundos
    plan = estado["plan"]
    assert [d["dia"] for d in plan["dias"]] == ["martes", "jueves", "viernes", "sabado"]
    assert all(d["enfoque"] and d["explicacion"] for d in plan["dias"])
    assert plan["origen"] == "ia" and plan["modelo"] == "simulada" and plan["version"] == 1
    # El perfil queda con la misma cantidad de días que se eligió.
    assert client.get("/api/perfil", headers=h).json()["dias_por_semana"] == 4
    assert not client.get("/api/perfil", headers=h).json()["plan_requiere_regenerar"]
    # Cada grupo muscular grande, al menos una vez por semana.
    grupos = grupos_por_codigo(db)
    assert set(reglas.GRUPOS_GRANDES) <= {grupos[c] for c in codigos_plan(plan)}


@pytest.mark.parametrize("minutos,esperado", [(20, 4), (45, 5), (60, 7), (120, 8)])
def test_cantidad_de_ejercicios_segun_los_minutos(client, usuario_listo, minutos, esperado):
    h = usuario_listo(minutos_por_sesion=minutos)
    plan = generar(client, h, ["lunes", "jueves"])["plan"]
    assert {len(d["ejercicios"]) for d in plan["dias"]} == {esperado}
    assert all(reglas.MIN_EJERCICIOS <= len(d["ejercicios"]) <= reglas.MAX_EJERCICIOS for d in plan["dias"])


def test_regenerar_crea_otra_version_y_se_puede_hasta_3_veces_al_dia(client, usuario_listo):
    h = usuario_listo()
    primero = generar(client, h)
    assert primero["plan"]["motivo"] == "primera" and primero["regeneraciones_restantes"] == 3
    for n in range(3):
        estado = generar(client, h)
        assert estado["plan"]["version"] == n + 2 and estado["plan"]["motivo"] == "regenerar"
    assert estado["regeneraciones_restantes"] == 0
    r = client.post("/api/plan", json={}, headers=h)
    assert r.status_code == 429 and r.json()["codigo"] == "limite_regeneraciones"
    assert client.get("/api/plan", headers=h).json()["plan"]["version"] == 4  # sigue el último


def test_si_el_perfil_cambia_se_sugiere_regenerar(client, usuario_listo):
    h = usuario_listo()
    generar(client, h)
    assert not client.get("/api/plan", headers=h).json()["perfil_cambio"]
    client.put("/api/perfil", json={"objetivo": "fuerza"}, headers=h)
    assert client.get("/api/plan", headers=h).json()["perfil_cambio"]


def test_dias_repetidos_o_invalidos_se_rechazan(client, usuario_listo):
    h = usuario_listo()
    assert client.post("/api/plan", json={"dias": ["lunes", "lunes"]}, headers=h).status_code == 422
    assert client.post("/api/plan", json={"dias": ["feriado"]}, headers=h).status_code == 422


# ---------------- PG-24 ----------------
@pytest.mark.parametrize("dias,esquema", [
    (["miercoles"], "cuerpo_completo"),
    (["lunes", "jueves"], "cuerpo_completo"),
    (["domingo", "lunes"], "torso_pierna"),  # domingo y lunes son seguidos
    (["lunes", "miercoles", "viernes"], "cuerpo_completo"),
    (["lunes", "martes", "miercoles"], "division"),  # días seguidos: no se repite cuerpo completo
    (["lunes", "martes", "jueves", "viernes"], "torso_pierna"),
    (["lunes", "martes", "miercoles", "viernes", "sabado"], "division"),
    (list(DIAS_SEMANA[:6]), "division"),
    (list(DIAS_SEMANA), "division"),
])
def test_esquema_segun_los_dias(dias, esquema):
    assert ctx_ficticio(dias).esquema == esquema


def test_nunca_el_mismo_grupo_principal_en_dos_dias_seguidos_con_cualquier_combinacion():
    for n in range(1, 8):
        for dias in itertools.combinations(DIAS_SEMANA, n):
            ctx = ctx_ficticio(list(dias))
            revision = reglas.validar(reglas.armar_con_reglas(ctx), ctx)
            assert revision.ok, (dias, revision.errores)
            for a, b in itertools.combinations(revision.plan.dias, 2):
                if reglas.son_seguidos(a.dia, b.dia):
                    assert not set(a.grupos) & set(b.grupos), (dias, a.dia, b.dia)


# ---------------- PG-25 ----------------
@pytest.mark.parametrize("objetivo,tipo", [("fuerza", "fuerza"), ("ganar_musculo", "musculo"), ("resistencia", "resistencia"),
                                           ("bajar_grasa", "musculo"), ("salud_general", "musculo")])
def test_series_repeticiones_y_descanso_dentro_del_rango_del_objetivo(client, usuario_listo, db, objetivo, tipo):
    h = usuario_listo(objetivo=objetivo, nivel="avanzado")
    plan = generar(client, h, ["lunes", "miercoles", "viernes"])["plan"]
    r = reglas.RANGOS[tipo]
    multi = {e.codigo: e.multiarticular for e in db.query(Ejercicio)}
    for d in plan["dias"]:
        for e in d["ejercicios"]:
            assert r["series"][0] <= e["series"] <= r["series"][1]
            assert r["reps"][0] <= e["reps_min"] <= e["reps_max"] <= r["reps"][1]
            assert r["descanso"][0] <= e["descanso_seg"] <= r["descanso"][1]
            # Los básicos (varias articulaciones) llevan el descanso más largo del rango.
            assert e["descanso_seg"] == (r["descanso"][1] if multi[e["ejercicio"]["codigo"]] else r["descanso"][0])


def test_principiante_maximo_3_series_y_menos_volumen(client, usuario_listo):
    h = usuario_listo(objetivo="fuerza", nivel="principiante")
    plan = generar(client, h)["plan"]
    assert max(e["series"] for d in plan["dias"] for e in d["ejercicios"]) <= 3
    h2 = usuario_listo("b@pulsegym.app", objetivo="fuerza", nivel="avanzado")
    avanzado = generar(client, h2)["plan"]
    assert max(e["series"] for d in avanzado["dias"] for e in d["ejercicios"]) == 5


# ---------------- PG-20 ----------------
def test_con_rodilla_activa_20_planes_seguidos_no_incluyen_ningun_ejercicio_contraindicado(client, usuario_listo, db, cfg):
    cfg(plan_regeneraciones_dia=100, ia_limite_planes_dia=100)
    h = usuario_listo()
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda"}, headers=h)
    prohibidos = contraindicados(db, "rodilla")  # evitar Y precaución: la lesión está activa
    combinaciones = [list(c) for n in (2, 3, 4, 5) for c in itertools.combinations(DIAS_SEMANA, n)][:20]
    for i, dias in enumerate(combinaciones):
        client.put("/api/perfil", json={"objetivo": ["fuerza", "ganar_musculo", "resistencia", "bajar_grasa"][i % 4]}, headers=h)
        plan = generar(client, h, dias)["plan"]
        assert not prohibidos & set(codigos_plan(plan)), dias
        assert plan["lesiones"] == [{"zona": "rodilla", "nombre": "Rodilla", "estado": "activa"}]
        assert plan["ejercicios_excluidos"] > 0
        assert "rodilla" in plan["explicacion"].lower()


def test_en_reintroduccion_lo_de_precaucion_puede_aparecer_marcado_y_lo_de_evitar_nunca(client, usuario_listo, db):
    h = usuario_listo()
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "cronica", "estado": "reintroduccion"}, headers=h)
    plan = generar(client, h, ["lunes", "jueves"])["plan"]
    precaucion = contraindicados(db, "rodilla", ("precaucion",))
    assert not contraindicados(db, "rodilla", ("evitar",)) & set(codigos_plan(plan))
    for d in plan["dias"]:
        for e in d["ejercicios"]:
            assert e["precaucion"] == (e["ejercicio"]["codigo"] in precaucion)


def test_una_lesion_nueva_regenera_el_plan_sola(client, usuario_listo, db):
    h = usuario_listo()
    v1 = generar(client, h, ["lunes", "jueves"])["plan"]
    lid = client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=h).json()["id"]
    estado = client.get("/api/plan", headers=h).json()
    assert estado["plan"]["version"] == 2 and estado["plan"]["motivo"] == "lesion"
    assert not contraindicados(db, "hombro") & set(codigos_plan(estado["plan"]))
    assert estado["regeneraciones_restantes"] == 3  # lo automático no cuenta como regeneración del usuario
    assert [d["dia"] for d in estado["plan"]["dias"]] == [d["dia"] for d in v1["dias"]]
    # Al recuperarse, se vuelve a regenerar (ya puede volver lo que estaba excluido).
    client.patch(f"/api/lesiones/{lid}", json={"estado": "recuperada"}, headers=h)
    estado = client.get("/api/plan", headers=h).json()
    assert estado["plan"]["version"] == 3 and estado["plan"]["lesiones"] == []
    assert client.get("/api/plan", headers=h).json()["plan"]["version"] == 3  # sin cambios, no se regenera


def test_si_no_queda_ningun_ejercicio_para_un_grupo_se_omite_y_se_avisa(client, usuario_listo, db):
    tobillo = db.query(ZonaLesion).filter_by(codigo="tobillo").one()
    pantorrillas = db.query(GrupoMuscular).filter_by(codigo="pantorrillas").one()
    for e in db.query(Ejercicio):
        if e.musculo_principal and e.musculo_principal.id == pantorrillas.id:
            existente = next((c for c in e.contraindicaciones if c.zona_id == tobillo.id), None)
            if existente:
                existente.nivel = "evitar"
            else:
                db.add(EjercicioContraindicacion(ejercicio_id=e.id, zona_id=tobillo.id, nivel="evitar"))
    db.commit()
    h = usuario_listo()
    client.post("/api/lesiones", json={"zona": "tobillo", "tipo": "aguda"}, headers=h)
    plan = generar(client, h, ["lunes", "martes", "jueves", "viernes"])["plan"]
    grupos = grupos_por_codigo(db)
    assert "pantorrillas" not in {grupos[c] for c in codigos_plan(plan)}
    assert any("pantorrillas" in a.lower() and "lesion" in reglas.sin_tildes(a) for a in plan["avisos"])
    assert all(len(d["ejercicios"]) >= reglas.MIN_EJERCICIOS for d in plan["dias"])


def test_el_plan_solo_usa_lo_que_hay_en_mis_gyms(client, usuario_listo, gym, db):
    h = usuario_listo()
    _, gid = gym(h=h)  # gym vacío, solo con mancuernas
    client.put(f"/api/gyms/{gid}/implementos", json={"implementos": ["mancuernas"]}, headers=h)
    plan = generar(client, h)["plan"]
    for d in plan["dias"]:
        for e in d["ejercicios"]:
            assert e["ejercicio"]["categoria_equipo"] == "sin_equipo" or "Mancuernas" in e["ejercicio"]["maquinas"], e


# ---------------- PG-26 ----------------
# La IA se pide en paralelo: un pedido para la explicación general y uno por día. Cada respuesta se valida sola.
def _valido(ctx, pedido):
    return "modelo-prueba", plan_ia._plan_simulada(ctx, pedido, 0)[1]


def _llamadas(db, tipo="plan"):
    db.expire_all()
    return db.query(LlamadaIA).filter_by(tipo=tipo).order_by(LlamadaIA.id).all()


def _del_dia(llamadas, dia):
    return [x for x in llamadas if (x.detalle or "").startswith(dia)]


def test_respuesta_sin_el_formato_fijo_se_rechaza_y_se_pide_de_nuevo(client, usuario_listo, ia_plan, db):
    vistos = set()

    def falsa(ctx, pedido, _limite):
        if pedido.dia == "lunes" and "lunes" not in vistos:
            vistos.add("lunes")
            return "modelo-prueba", {"plan": "lunes pecho"}
        return _valido(ctx, pedido)

    ia_plan(falsa)
    plan = generar(client, usuario_listo(), ["lunes", "jueves"])["plan"]
    assert plan["origen"] == "ia" and plan["modelo"] == "modelo-prueba"
    lunes = _del_dia(_llamadas(db), "lunes")
    assert [x.resultado for x in lunes] == ["rechazada", "ok"] and "formato" in lunes[0].detalle


def test_un_ejercicio_contraindicado_se_rechaza_con_su_motivo_y_la_ia_recibe_el_error(client, usuario_listo, ia_plan, db):
    vistos: list[list[str]] = []

    def falsa(ctx, pedido, _limite):
        datos = _valido(ctx, pedido)[1]
        if pedido.dia == "jueves":  # en este plan el jueves es de pierna
            vistos.append(list(pedido.errores_previos))
            if len(vistos) == 1:
                datos["ejercicios"][0]["codigo"] = "EXT_CUADRICEPS"  # rodilla: evitar
        return "modelo-prueba", datos

    ia_plan(falsa)
    h = usuario_listo()
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda"}, headers=h)
    plan = generar(client, h, ["lunes", "jueves"])["plan"]
    assert "EXT_CUADRICEPS" not in codigos_plan(plan) and plan["origen"] == "ia"
    rechazo = _del_dia(_llamadas(db), "jueves")[0]
    assert rechazo.resultado == "rechazada" and "EXT_CUADRICEPS" in rechazo.detalle and "contraindicado" in rechazo.detalle
    assert vistos[0] == [] and any("EXT_CUADRICEPS" in e for e in vistos[1])


DANOS = ["codigo_inventado", "otro_grupo", "repetido", "pocos", "sin_grupo_obligatorio"]


def _danar(ctx, pedido, dano):
    datos = _valido(ctx, pedido)[1]
    ej = datos["ejercicios"]
    if dano == "codigo_inventado":
        ej[0]["codigo"] = "PRESS_INVENTADO"
    elif dano == "otro_grupo":  # un ejercicio que no corresponde al enfoque del día
        ej[0]["codigo"] = "PRENSA_45" if ctx.permitidos[ej[0]["codigo"]].grupo in ("pecho", "espalda", "hombros") else "PRESS_BANCA_BARRA"
    elif dano == "repetido":
        ej[1] = dict(ej[0])
    elif dano == "pocos":
        del ej[2:]
    else:
        quitar = pedido.obligatorios[0]
        datos["ejercicios"] = [e for e in ej if ctx.permitidos[e["codigo"]].grupo != quitar]
    return "modelo-prueba", datos


@pytest.mark.parametrize("dano", DANOS)
def test_un_dia_que_no_pasa_la_validacion_se_reintenta_2_veces_y_luego_usa_reglas(client, usuario_listo, ia_plan, db, dano):
    ia_plan(lambda ctx, pedido, _l: _danar(ctx, pedido, dano) if pedido.dia == "lunes" else _valido(ctx, pedido))
    plan = generar(client, usuario_listo(), ["lunes", "martes", "jueves", "viernes"])["plan"]
    # 1 intento + 2 reintentos (PG-26), todos rechazados con su motivo → ese día usa la versión de reglas.
    lunes = _del_dia(_llamadas(db), "lunes")
    assert [x.resultado for x in lunes] == ["rechazada"] * 3 and all(len(x.detalle) > len("lunes: ") for x in lunes)
    assert plan["origen"] == "mixto" and "reglas" in plan["explicacion"]
    assert "PRESS_INVENTADO" not in codigos_plan(plan)
    assert all(len(d["ejercicios"]) >= 4 for d in plan["dias"])


def test_si_ningun_dia_pasa_la_validacion_se_usa_la_version_de_solo_reglas(client, usuario_listo, ia_plan, db):
    ia_plan(lambda ctx, pedido, _l: _danar(ctx, pedido, "codigo_inventado") if pedido.dia else _valido(ctx, pedido))
    plan = generar(client, usuario_listo(), ["lunes", "jueves"])["plan"]
    assert plan["origen"] == "reglas" and plan["modelo"] is None and "reglas" in plan["explicacion"]
    assert sum(1 for x in _llamadas(db) if x.resultado == "rechazada") == 6  # 2 días × 3 intentos


def test_las_series_y_descansos_los_pone_el_sistema_aunque_la_ia_mande_otros(client, usuario_listo, ia_plan):
    def falsa(ctx, pedido, _l):
        datos = _valido(ctx, pedido)[1]
        for e in datos.get("ejercicios", []):
            e.update(series=9, reps_min=30, reps_max=2, descanso_seg=5)
        return "modelo-prueba", datos

    ia_plan(falsa)
    plan = generar(client, usuario_listo(nivel="principiante"))["plan"]
    assert plan["origen"] == "ia"
    r = reglas.RANGOS["musculo"]
    for e in (e for d in plan["dias"] for e in d["ejercicios"]):
        assert e["series"] == 3 and r["reps"][0] <= e["reps_min"] <= e["reps_max"] <= r["reps"][1]
        assert r["descanso"][0] <= e["descanso_seg"] <= r["descanso"][1]


def test_si_la_ia_falla_se_usa_la_version_de_solo_reglas(client, usuario_listo, ia_plan, db):
    def falla(*_):
        raise ErrorIA("Se alcanzó el límite gratuito de la IA por minuto.")

    ia_plan(falla)
    plan = generar(client, usuario_listo(), ["lunes", "jueves"])["plan"]
    assert plan["origen"] == "reglas"
    assert [x.resultado for x in _llamadas(db)] == ["error"] * 3  # general + 2 días, sin reintentos inútiles


def test_si_la_ia_es_lenta_no_se_pasa_del_tiempo_maximo(client, usuario_listo, ia_plan, cfg, db):
    cfg(plan_tiempo_max_seg=2.5, ia_duplicar_tras_seg=None)

    def lenta(ctx, pedido, _l):
        time.sleep(1.0)
        return "modelo-prueba", {"x": 1}  # inválida: obliga a reintentar

    ia_plan(lenta)
    inicio = time.perf_counter()
    plan = generar(client, usuario_listo(), ["lunes", "jueves"])["plan"]
    assert time.perf_counter() - inicio < 3.5 and plan["origen"] == "reglas"
    assert len(_llamadas(db)) == 3  # tras la primera ronda no quedaban 2 s para otra


def test_un_pedido_lento_se_duplica_y_se_usa_la_respuesta_que_llega_primero(client, usuario_listo, ia_plan, cfg, db):
    cfg(ia_duplicar_tras_seg=0.3)
    vistos: set[str] = set()
    candado = threading.Lock()

    def irregular(ctx, pedido, limite):
        with candado:
            primera = pedido.clave not in vistos
            vistos.add(pedido.clave)
        if primera and pedido.dia == "lunes":
            time.sleep(min(limite, 3.0))  # la primera copia del lunes "se cuelga"
        return _valido(ctx, pedido)

    ia_plan(irregular)
    inicio = time.perf_counter()
    plan = generar(client, usuario_listo(), ["lunes", "jueves"])["plan"]
    assert time.perf_counter() - inicio < 2.5 and plan["origen"] == "ia"
    assert [x.resultado for x in _llamadas(db)].count("copia") == 1


# ---------------- PG-27 ----------------
def test_la_explicacion_es_breve_simple_y_se_guarda_con_la_version(client, usuario_listo, ia_plan):
    def charlatana(ctx, pedido, _l):
        if pedido.tipo == "general":
            return "modelo-prueba", {"explicacion": "Este plan busca hipertrofia con sobrecarga progresiva."}
        datos = _valido(ctx, pedido)[1]
        datos["explicacion"] = "Una. Dos. Tres. Cuatro. Cinco."
        for e in datos["ejercicios"]:
            e["motivo"] = "Primera frase. Segunda frase que sobra."
        return "modelo-prueba", datos

    ia_plan(charlatana)
    h = usuario_listo()
    client.post("/api/lesiones", json={"zona": "codo", "tipo": "aguda"}, headers=h)
    plan = generar(client, h)["plan"]
    assert "hipertrofia" not in plan["explicacion"] and "crecimiento muscular" in plan["explicacion"]
    assert "codo" in plan["explicacion"].lower()  # se agregó cómo se cuidó la lesión
    for d in plan["dias"]:
        assert d["explicacion"] == "Una. Dos. Tres."
        assert all(e["motivo"] == "Primera frase." for e in d["ejercicios"])
    # Se guarda con la versión: al pedir el plan otra vez, sigue igual.
    assert client.get("/api/plan", headers=h).json()["plan"]["explicacion"] == plan["explicacion"]


def test_la_explicacion_de_reglas_menciona_objetivo_y_lesion(client, usuario_listo, ia_plan):
    ia_plan(lambda *_: (_ for _ in ()).throw(ErrorIA("sin IA")))
    h = usuario_listo(objetivo="fuerza")
    client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=h)
    plan = generar(client, h)["plan"]
    texto = plan["explicacion"].lower()
    assert "ganar fuerza" in texto and "hombro" in texto and "cuerpo completo" in texto
    assert all(e["motivo"].count(".") == 1 for d in plan["dias"] for e in d["ejercicios"])


def test_a_la_ia_no_se_le_envian_nombre_correo_ni_descripciones(client, usuario_listo, ia_plan):
    prompts = []
    ia_plan(lambda ctx, pedido, _l: (prompts.append(
        plan_ia.prompt_general(ctx) if pedido.tipo == "general" else plan_ia.prompt_dia(ctx, pedido)) or _valido(ctx, pedido)))
    h = usuario_listo()
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda", "descripcion": "Me caí jugando fútbol con Pedro"}, headers=h)
    generar(client, h)
    texto = " ".join(prompts)
    assert "Rodilla" in texto and "Pedro" not in texto and "Ana" not in texto and "@" not in texto


# ---------------- PG-49 (plan) ----------------
def test_al_llegar_al_limite_diario_de_planes_con_ia_se_usan_las_reglas(client, usuario_listo, cfg):
    cfg(ia_limite_planes_dia=1)
    h = usuario_listo()
    assert generar(client, h)["plan"]["origen"] == "ia"
    plan = generar(client, h)["plan"]
    assert plan["origen"] == "reglas" and "reglas" in plan["explicacion"]
    uso = {t["tipo"]: t for t in client.get("/api/ia/uso", headers=h).json()["tipos"]}
    assert uso["plan"] == {"tipo": "plan", "usadas": 1, "limite": 1}


def test_cada_llamada_registra_tokens_y_costo_estimado(client, usuario_listo, ia_plan, db, cfg):
    cfg(ia_precio_entrada_usd_millon=1.0, ia_precio_salida_usd_millon=2.0)
    ia_plan(lambda ctx, pedido, _l: ia_cliente.RespuestaIA("modelo-prueba", _valido(ctx, pedido)[1], 1000, 500))
    h = usuario_listo()
    generar(client, h, ["lunes", "jueves"])
    llamadas = _llamadas(db)
    assert len(llamadas) == 3 and all((x.tokens_entrada, x.tokens_salida, x.costo_usd) == (1000, 500, 0.002) for x in llamadas)
    assert client.get("/api/ia/uso", headers=h).json()["costo_hoy_usd"] == 0.006


def test_alerta_al_equipo_si_el_costo_del_dia_supera_el_tope(client, usuario_listo, ia_plan, cfg):
    from app.services import correo

    cfg(ia_costo_tope_diario_usd=0.001, ia_alerta_email="equipo@pulsegym.app", plan_regeneraciones_dia=10)
    ia_plan(lambda ctx, pedido, _l: ia_cliente.RespuestaIA("modelo-prueba", _valido(ctx, pedido)[1], 10_000, 1_000))
    h = usuario_listo()
    generar(client, h)
    generar(client, h)
    alertas = [c for c in correo.BUZON_DE_PRUEBA if c["para"] == "equipo@pulsegym.app"]
    assert len(alertas) == 1 and "tope" in alertas[0]["asunto"]  # una sola vez por día
