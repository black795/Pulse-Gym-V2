"""PG-19: registro de lesiones."""
from app.models import Usuario

ZONAS = {"hombro", "codo", "muneca", "cuello", "espalda_alta", "espalda_baja", "cadera", "rodilla", "tobillo"}


def test_la_zona_se_elige_de_una_lista_fija(client, registrar):
    z = client.get("/api/zonas-lesion", headers=registrar()).json()
    assert {x["codigo"] for x in z} == ZONAS


def test_registrar_una_lesion_pide_consentimiento(client, registrar):
    r = client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda"}, headers=registrar())
    assert r.status_code == 403 and r.json()["codigo"] == "consentimiento_requerido"


def test_registra_zona_tipo_dolor_con_carga_y_descripcion(client, con_consentimiento):
    h = con_consentimiento()
    r = client.post("/api/lesiones", headers=h, json={
        "zona": "rodilla", "tipo": "aguda", "duele_con_carga": True, "descripcion": "Torcedura jugando fútbol",
    })
    assert r.status_code == 201
    l = r.json()
    assert (l["zona"]["codigo"], l["zona"]["nombre"], l["tipo"], l["duele_con_carga"], l["estado"]) == ("rodilla", "Rodilla", "aguda", True, "activa")
    assert l["descripcion"] == "Torcedura jugando fútbol"


def test_permite_varias_lesiones_a_la_vez(client, con_consentimiento):
    h = con_consentimiento()
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda"}, headers=h)
    client.post("/api/lesiones", json={"zona": "hombro", "tipo": "cronica"}, headers=h)
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "cronica"}, headers=h)  # incluso en la misma zona
    assert len(client.get("/api/lesiones", headers=h).json()["lesiones"]) == 3


def test_zona_o_tipo_invalidos_se_rechazan(client, con_consentimiento):
    h = con_consentimiento()
    assert client.post("/api/lesiones", json={"zona": "oreja", "tipo": "aguda"}, headers=h).status_code == 400
    assert client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "rara"}, headers=h).status_code == 422
    assert client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "aguda", "estado": "recuperada"}, headers=h).status_code == 422


def test_estados_activa_reintroduccion_recuperada_y_el_historial_se_conserva(client, con_consentimiento):
    h = con_consentimiento()
    lid = client.post("/api/lesiones", json={"zona": "codo", "tipo": "aguda"}, headers=h).json()["id"]

    assert client.patch(f"/api/lesiones/{lid}", json={"estado": "reintroduccion"}, headers=h).json()["estado"] == "reintroduccion"
    rec = client.patch(f"/api/lesiones/{lid}", json={"estado": "recuperada"}, headers=h).json()
    assert rec["estado"] == "recuperada" and rec["recuperada_at"]

    todas = client.get("/api/lesiones", headers=h).json()["lesiones"]
    assert [l["estado"] for l in todas] == ["recuperada"]  # sigue en el historial
    assert client.get("/api/lesiones?incluir_recuperadas=false", headers=h).json()["lesiones"] == []

    # Si recae, vuelve a activa y se borra la fecha de recuperación.
    rec = client.patch(f"/api/lesiones/{lid}", json={"estado": "activa"}, headers=h).json()
    assert rec["estado"] == "activa" and rec["recuperada_at"] is None


def test_marcar_una_lesion_activa_marca_el_plan_para_regenerarse(client, con_consentimiento, db):
    h = con_consentimiento()
    uid = db.query(Usuario).filter_by(email="ana@pulsegym.app").one().id

    def flag():
        db.expire_all()
        return db.get(Usuario, uid).plan_requiere_regenerar

    assert flag() is False
    lid = client.post("/api/lesiones", json={"zona": "espalda_baja", "tipo": "cronica"}, headers=h).json()["id"]
    assert flag() is True
    assert client.get("/api/perfil", headers=h).json()["plan_requiere_regenerar"] is True


def test_siempre_muestra_el_aviso_medico(client, con_consentimiento):
    aviso = client.get("/api/lesiones", headers=con_consentimiento()).json()["aviso"]
    assert "no reemplaza a un médico" in aviso and "profesional" in aviso


def test_nadie_puede_tocar_las_lesiones_de_otra_persona(client, con_consentimiento):
    ana = con_consentimiento("ana@pulsegym.app")
    luis = con_consentimiento("luis@pulsegym.app")
    lid = client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=ana).json()["id"]
    assert client.patch(f"/api/lesiones/{lid}", json={"estado": "recuperada"}, headers=luis).status_code == 404
    assert client.get("/api/lesiones", headers=luis).json()["lesiones"] == []


def test_cambiar_sin_enviar_nada_se_rechaza(client, con_consentimiento):
    h = con_consentimiento()
    lid = client.post("/api/lesiones", json={"zona": "codo", "tipo": "aguda"}, headers=h).json()["id"]
    assert client.patch(f"/api/lesiones/{lid}", json={}, headers=h).status_code == 400
