"""PG-15, PG-16, PG-17, PG-18: catálogo, validación, carga repetible y alternativas."""
import copy

from app.models import Ejercicio, EjercicioContraindicacion, MaquinaCatalogo
from app.scripts import cargar_catalogo as cc


def codigos(lista):
    return [x["codigo"] for x in lista]


# ---------------- los archivos del catálogo
def test_los_archivos_del_catalogo_son_validos_y_cumplen_las_metas():
    datos = cc.leer_datos()
    inf = cc.validar(datos)
    assert inf.errores == []
    r = inf.resumen
    assert 30 <= r["maquinas"] <= 50  # PG-15
    assert r["ejercicios"] >= 80 and r["sin_equipo"] >= 20  # PG-16
    # Lo único pendiente es lo que no se puede inventar: las fotos de referencia.
    assert all("foto de referencia" in a for a in inf.avisos)


def test_modo_estricto_exige_fotos_de_referencia():
    # Hoy todas las máquinas ya tienen foto (insumo del reconocimiento con IA, Sprint 2).
    assert cc.validar(cc.leer_datos(), estricto=True).ok
    datos = copy.deepcopy(cc.leer_datos())
    datos["maquinas"][0]["fotos"] = []
    inf = cc.validar(datos, estricto=True)
    assert not inf.ok and all("foto de referencia" in e for e in inf.errores)


def test_los_datos_de_cada_ejercicio_estan_completos():
    for e in cc.leer_datos()["ejercicios"]:
        assert e["musculo_principal"] and e["instrucciones"] and e["dificultad"] in cc.DIFICULTADES, e["codigo"]
        assert e["contraindicaciones_revisadas"] is False  # nada se usa con usuarios reales sin revisión del entrenador


def test_cada_grupo_muscular_tiene_alternativas_y_una_sin_equipo():
    por_grupo: dict = {}
    for e in cc.leer_datos()["ejercicios"]:
        por_grupo.setdefault(e["musculo_principal"], []).append(e)
    for g, lista in por_grupo.items():
        assert len(lista) >= 3, g
        assert any(x["categoria_equipo"] == "sin_equipo" for x in lista), g


# ---------------- el script valida antes de insertar
def test_el_script_detecta_errores_de_datos():
    base = cc.leer_datos()

    def con(mutar):
        d = copy.deepcopy(base)
        mutar(d)
        return cc.validar(d).errores

    assert any("repetido" in e for e in con(lambda d: d["maquinas"].append(dict(d["maquinas"][0]))))
    assert any("MAYÚSCULAS" in e for e in con(lambda d: d["maquinas"][0].update(codigo="prensa 45")))
    assert any("no existe" in e and "músculo" in e or "músculo principal" in e for e in con(lambda d: d["ejercicios"][0].update(musculo_principal="cejas")))
    assert any("no existe" in e for e in con(lambda d: d["ejercicios"][0].update(maquinas=["NO_EXISTE"])))
    assert any("ningún ejercicio" in e for e in con(lambda d: d["maquinas"].append({"codigo": "HUERFANA", "nombre": "X", "tipo": "polea", "fotos": []})))
    assert any("zona de lesión" in e for e in con(lambda d: d["ejercicios"][0].update(contraindicaciones=[{"zona": "oreja", "nivel": "evitar"}])))
    assert any("sin_equipo" in e and "máquinas asignadas" in e for e in con(lambda d: d["ejercicios"][0].update(categoria_equipo="sin_equipo")))


def test_si_hay_errores_no_se_inserta_nada(db):
    datos = cc.leer_datos()
    datos["ejercicios"][0]["musculo_principal"] = "cejas"
    n = db.query(Ejercicio).count()
    inf, conteo = cc.cargar(db, datos)
    assert not inf.ok and conteo == {"creados": 0, "actualizados": 0} and db.query(Ejercicio).count() == n


# ---------------- carga repetible (no duplica)
def test_volver_a_correr_el_script_no_duplica_datos(db):
    antes = (db.query(MaquinaCatalogo).count(), db.query(Ejercicio).count(), db.query(EjercicioContraindicacion).count())
    assert antes[0] >= 42 and antes[1] >= 100  # ya se cargó al crear la base
    for _ in range(2):
        inf, conteo = cc.cargar(db)
        assert inf.ok and conteo == {"creados": 0, "actualizados": 0}
    assert (db.query(MaquinaCatalogo).count(), db.query(Ejercicio).count(), db.query(EjercicioContraindicacion).count()) == antes


def test_el_script_actualiza_lo_que_cambio_y_la_revision_del_entrenador_se_reinicia_si_cambian_las_contraindicaciones(db):
    e = db.query(Ejercicio).filter_by(codigo="PRENSA_45").one()
    e.contraindicaciones_revisadas = True
    db.commit()

    # Cambia solo el nombre: la revisión se conserva.
    datos = cc.leer_datos()
    nuevo = next(x for x in datos["ejercicios"] if x["codigo"] == "PRENSA_45")
    nuevo["nombre"] = "Prensa 45° (renombrada)"
    _, conteo = cc.cargar(db, datos)
    db.expire_all()
    e = db.query(Ejercicio).filter_by(codigo="PRENSA_45").one()
    assert conteo["actualizados"] == 1 and e.nombre.endswith("(renombrada)") and e.contraindicaciones_revisadas is True

    # Cambia una contraindicación: hay que revisarla de nuevo.
    nuevo["contraindicaciones"] = [{"zona": "tobillo", "nivel": "evitar"}]
    cc.cargar(db, datos)
    db.expire_all()
    e = db.query(Ejercicio).filter_by(codigo="PRENSA_45").one()
    assert [(c.zona.codigo, c.nivel) for c in e.contraindicaciones] == [("tobillo", "evitar")]
    assert e.contraindicaciones_revisadas is False


# ---------------- consulta
def test_lista_maquinas_con_otros_nombres_y_cantidad_de_ejercicios(client, registrar):
    m = client.get("/api/catalogo/maquinas", headers=registrar()).json()
    prensa = next(x for x in m if x["codigo"] == "PRENSA_45")
    assert "Leg press" in prensa["otros_nombres"] and prensa["ejercicios"] >= 2 and prensa["tipo"] == "maquina_guiada"
    assert len(m) >= 42


def test_una_maquina_desactivada_no_se_ofrece(client, registrar, db):
    h = registrar()
    db.query(MaquinaCatalogo).filter_by(codigo="ELIPTICA").one().activa = False
    db.commit()
    assert "ELIPTICA" not in codigos(client.get("/api/catalogo/maquinas", headers=h).json())
    ej = client.get("/api/catalogo/ejercicios?grupo=cardio", headers=h).json()
    eliptica = next(e for e in client.get("/api/catalogo/ejercicios", headers=h).json() if e["codigo"] == "ELIPTICA")
    alt = client.get(f"/api/catalogo/ejercicios/{next(e['id'] for e in ej if e['codigo'] == 'BICICLETA_ESTATICA')}/alternativas", headers=h).json()
    assert "ELIPTICA" not in codigos(alt)  # el ejercicio de la elíptica ya no se propone
    assert eliptica["maquinas"][0]["codigo"] == "ELIPTICA"  # pero el dato sigue existiendo


def test_ficha_del_ejercicio(client, registrar):
    h = registrar()
    lista = client.get("/api/catalogo/ejercicios?grupo=pecho", headers=h).json()
    press = next(e for e in lista if e["codigo"] == "PRESS_PECHO_MAQ")
    f = client.get(f"/api/catalogo/ejercicios/{press['id']}", headers=h).json()
    assert f["musculo_principal"] == "pecho" and set(f["musculos_secundarios"]) == {"triceps", "hombros"}
    assert f["dificultad"] == "facil" and f["multiarticular"] is True and len(f["instrucciones"]) > 20
    assert f["contraindicaciones"] == [{"zona": "hombro", "zona_nombre": "Hombro", "nivel": "precaucion"}]
    assert f["contraindicaciones_revisadas"] is False
    assert client.get("/api/catalogo/ejercicios/99999", headers=h).status_code == 404


def test_filtros_de_ejercicios(client, registrar):
    h = registrar()
    sin = client.get("/api/catalogo/ejercicios?categoria=sin_equipo", headers=h).json()
    assert len(sin) >= 20 and all(e["maquinas"] == [] for e in sin)
    prensa = client.get("/api/catalogo/ejercicios?maquina=prensa_45", headers=h).json()
    assert {"PRENSA_45", "GEMELOS_EN_PRENSA"} <= set(codigos(prensa))
    assert client.get("/api/catalogo/ejercicios?categoria=inventada", headers=h).status_code == 422


def test_el_catalogo_requiere_sesion(client):
    assert client.get("/api/catalogo/maquinas").status_code == 401


# ---------------- PG-17: alternativas
def _id(client, h, codigo):
    return next(e["id"] for e in client.get("/api/catalogo/ejercicios", headers=h).json() if e["codigo"] == codigo)


def test_alternativas_siguen_el_orden_maquina_peso_libre_sin_equipo(client, registrar):
    h = registrar()
    alt = client.get(f"/api/catalogo/ejercicios/{_id(client, h, 'PRENSA_45')}/alternativas?limite=50", headers=h).json()
    assert alt and "PRENSA_45" not in codigos(alt)
    assert all(a["musculo_principal"] == "cuadriceps" for a in alt)
    niveles = [a["nivel_busqueda"] for a in alt]
    assert niveles == sorted(niveles) and set(niveles) == {1, 2, 3}
    assert next(a for a in alt if a["nivel_busqueda"] == 1)["categoria_equipo"] == "maquina"
    assert all(a["categoria_equipo"] == "sin_equipo" for a in alt if a["nivel_busqueda"] == 3)


def test_alternativas_con_las_maquinas_disponibles_del_gym(client, registrar):
    h = registrar()
    alt = client.get(f"/api/catalogo/ejercicios/{_id(client, h, 'PRENSA_45')}/alternativas?maquinas=PRENSA_HORIZONTAL", headers=h).json()
    por_nivel = {n: codigos([a for a in alt if a["nivel_busqueda"] == n]) for n in (1, 2, 3)}
    assert por_nivel[1] == ["PRENSA_HORIZONTAL"]  # la única otra máquina que hay
    assert por_nivel[2] == []  # sin pesas en ese gym
    assert len(por_nivel[3]) >= 3  # calistenia siempre se puede


def test_todo_reemplazo_respeta_las_lesiones_del_usuario(client, con_consentimiento):
    h = con_consentimiento()
    pid = _id(client, h, "PRENSA_45")
    antes = codigos(client.get(f"/api/catalogo/ejercicios/{pid}/alternativas?limite=50", headers=h).json())
    assert "EXT_CUADRICEPS" in antes and "SENTADILLA_BARRA" in antes

    # Rodilla activa (PG-20): ni lo que se debe evitar (extensión de cuádriceps) ni lo que pide precaución
    # (sentadilla con barra) se propone mientras la lesión está activa.
    cid = client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda"}, headers=h).json()["id"]
    alt = client.get(f"/api/catalogo/ejercicios/{pid}/alternativas?limite=50", headers=h).json()
    assert "EXT_CUADRICEPS" not in codigos(alt) and "SENTADILLA_BARRA" not in codigos(alt)

    # En reintroducción, lo que pide precaución vuelve marcado; lo que se debe evitar, no.
    client.patch(f"/api/lesiones/{cid}", json={"estado": "reintroduccion"}, headers=h)
    alt = client.get(f"/api/catalogo/ejercicios/{pid}/alternativas?limite=50", headers=h).json()
    assert "EXT_CUADRICEPS" not in codigos(alt)
    assert next(a for a in alt if a["codigo"] == "SENTADILLA_BARRA")["precaucion"] is True

    # Espalda baja activa: la sentadilla con barra (espalda baja: evitar) también sale.
    lid = client.post("/api/lesiones", json={"zona": "espalda_baja", "tipo": "cronica"}, headers=h).json()["id"]
    assert "SENTADILLA_BARRA" not in codigos(client.get(f"/api/catalogo/ejercicios/{pid}/alternativas?limite=50", headers=h).json())
    client.patch(f"/api/lesiones/{lid}", json={"estado": "recuperada"}, headers=h)

    # Recuperada ya no limita.
    client.patch(f"/api/lesiones/{cid}", json={"estado": "recuperada"}, headers=h)
    assert "EXT_CUADRICEPS" in codigos(client.get(f"/api/catalogo/ejercicios/{pid}/alternativas?limite=50", headers=h).json())
