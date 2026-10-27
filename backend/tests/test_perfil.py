"""PG-02 (perfil) y PG-05 (consentimiento, retirar datos, borrar cuenta)."""
from app.db.base import ahora
from app.models import IntentoLogin, Lesion, Medicion, Usuario, UsuarioObjetivo
from app.services import correo
from tests.conftest import PASSWORD

PLAN = {"objetivo": "ganar_musculo", "nivel": "principiante", "dias_por_semana": 3, "minutos_por_sesion": 60}


# ---------------- perfil
def test_perfil_nuevo_esta_vacio_y_dice_que_falta(client, registrar):
    p = client.get("/api/perfil", headers=registrar()).json()
    assert p["puede_generar_plan"] is False
    assert set(p["faltan"]) == set(PLAN)
    assert p["imc"] is None and p["ultima_medicion"] is None


def test_objetivo_nivel_dias_y_minutos_son_lo_obligatorio_para_el_plan(client, registrar):
    h = registrar()
    for campo, valor in PLAN.items():
        p = client.put("/api/perfil", json={campo: valor}, headers=h).json()
    assert p["faltan"] == [] and p["puede_generar_plan"] is True


def test_grasa_y_masa_muscular_son_opcionales(client, con_consentimiento):
    h = con_consentimiento()
    p = client.put("/api/perfil", json={"edad": 30, "sexo": "femenino", "peso_kg": 60, "altura_cm": 165, **PLAN}, headers=h).json()
    assert p["puede_generar_plan"] is True
    assert p["ultima_medicion"]["grasa_pct"] is None and p["ultima_medicion"]["masa_muscular_kg"] is None


def test_calcula_imc_como_referencia(client, con_consentimiento):
    h = con_consentimiento()
    p = client.put("/api/perfil", json={"peso_kg": 70, "altura_cm": 175}, headers=h).json()
    assert p["imc"] == 22.9 and p["imc_categoria"] == "Peso normal"
    p = client.put("/api/perfil", json={"peso_kg": 95}, headers=h).json()
    assert p["imc"] == 31.0 and p["imc_categoria"] == "Obesidad"


def test_se_guarda_la_primera_medicion_con_fecha(client, con_consentimiento):
    h = con_consentimiento()
    client.put("/api/perfil", json={"peso_kg": 70, "altura_cm": 175, "grasa_pct": 22, "masa_muscular_kg": 30}, headers=h)
    m = client.get("/api/mediciones", headers=h).json()
    assert len(m) == 1 and m[0]["fecha"] == ahora().date().isoformat()
    assert (m[0]["peso_kg"], m[0]["grasa_pct"], m[0]["masa_muscular_kg"]) == (70, 22, 30)
    # Guardar de nuevo el mismo día actualiza esa medición, no crea otra.
    client.put("/api/perfil", json={"peso_kg": 69.5}, headers=h)
    m = client.get("/api/mediciones", headers=h).json()
    assert len(m) == 1 and m[0]["peso_kg"] == 69.5 and m[0]["grasa_pct"] == 22


def test_valida_los_rangos_de_la_tarjeta(client, con_consentimiento):
    h = con_consentimiento()
    malos = [
        {"edad": 15}, {"edad": 91}, {"peso_kg": 29}, {"peso_kg": 251}, {"altura_cm": 119}, {"altura_cm": 231},
        {"grasa_pct": 2}, {"grasa_pct": 61}, {"dias_por_semana": 0}, {"dias_por_semana": 8},
        {"minutos_por_sesion": 10}, {"objetivo": "volar"}, {"nivel": "dios"}, {"sexo": "x"},
    ]
    for cuerpo in malos:
        r = client.put("/api/perfil", json=cuerpo, headers=h)
        assert r.status_code == 422, cuerpo
    bordes = [{"edad": 16}, {"edad": 90}, {"peso_kg": 30}, {"peso_kg": 250}, {"altura_cm": 120}, {"altura_cm": 230}, {"grasa_pct": 3}, {"grasa_pct": 60}]
    for cuerpo in bordes:
        assert client.put("/api/perfil", json=cuerpo, headers=h).status_code == 200, cuerpo


def test_los_errores_de_validacion_vienen_en_espanol(client, con_consentimiento):
    h = con_consentimiento()
    assert client.put("/api/perfil", json={"edad": 15}, headers=h).json()["detail"] == "La edad debe ser al menos 16."
    assert client.put("/api/perfil", json={"peso_kg": 300}, headers=h).json()["detail"] == "El peso debe ser como máximo 250."


def test_un_envio_vacio_se_rechaza(client, registrar):
    assert client.put("/api/perfil", json={}, headers=registrar()).status_code == 400


# ---------------- consentimiento
def test_sin_consentimiento_no_se_guardan_datos_de_salud_pero_si_el_resto(client, registrar):
    h = registrar()
    for cuerpo in ({"peso_kg": 70}, {"altura_cm": 170}, {"grasa_pct": 20}, {"masa_muscular_kg": 30}):
        r = client.put("/api/perfil", json=cuerpo, headers=h)
        assert r.status_code == 403 and r.json()["codigo"] == "consentimiento_requerido", cuerpo
    # Puede usar la app: edad, sexo y plan no son datos sensibles.
    p = client.put("/api/perfil", json={"edad": 28, "sexo": "masculino", **PLAN}, headers=h)
    assert p.status_code == 200 and p.json()["puede_generar_plan"] is True


def test_rechazar_el_consentimiento_tambien_deja_usar_la_app(client, registrar):
    h = registrar()
    r = client.put("/api/consentimiento", json={"acepta": False}, headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "rechazado"
    assert client.put("/api/perfil", json=PLAN, headers=h).status_code == 200
    assert client.put("/api/perfil", json={"peso_kg": 70}, headers=h).status_code == 403


def test_al_aceptar_se_guarda_fecha_hora_y_version_del_texto(client, registrar):
    h = registrar()
    texto = client.get("/api/consentimiento/texto").json()
    assert texto["version"] and len(texto["secciones"]) >= 3
    assert [s["titulo"] for s in texto["secciones"]][:3] == ["Qué guardamos", "Para qué lo usamos", "Quién lo ve"]

    c = client.put("/api/consentimiento", json={"acepta": True}, headers=h).json()
    assert c["estado"] == "aceptado" and c["version_aceptada"] == texto["version"] and c["aceptado_at"]


def test_retirar_el_consentimiento_borra_los_datos_sensibles(client, con_consentimiento, db):
    h = con_consentimiento()
    client.put("/api/perfil", json={"peso_kg": 70, "altura_cm": 175, "edad": 30, **PLAN}, headers=h)
    client.post("/api/lesiones", json={"zona": "rodilla", "tipo": "cronica"}, headers=h)
    assert db.query(Medicion).count() == 1 and db.query(Lesion).count() == 1

    r = client.put("/api/consentimiento", json={"acepta": False}, headers=h)
    assert r.json()["estado"] == "rechazado" and r.json()["aceptado_at"] is None

    p = client.get("/api/perfil", headers=h).json()
    assert p["altura_cm"] is None and p["ultima_medicion"] is None and p["imc"] is None
    assert db.query(Medicion).count() == 0 and db.query(Lesion).count() == 0
    assert p["edad"] == 30 and p["puede_generar_plan"] is True  # lo no sensible se conserva


# ---------------- borrar cuenta
def test_eliminar_la_cuenta_borra_todo_y_envia_confirmacion(client, con_consentimiento, db):
    h = con_consentimiento("borrar@pulsegym.app")
    client.put("/api/perfil", json={"peso_kg": 70, "altura_cm": 175, "edad": 30, **PLAN}, headers=h)
    client.post("/api/lesiones", json={"zona": "hombro", "tipo": "aguda"}, headers=h)
    client.post("/api/auth/login", json={"email": "borrar@pulsegym.app", "password": "mala1234x"})  # deja un intento fallido
    assert db.query(IntentoLogin).count() == 1
    otros = db.query(Usuario).count()

    r = client.delete("/api/cuenta", headers=h)
    assert r.status_code == 204

    assert db.query(Usuario).count() == otros - 1
    assert db.query(Medicion).count() == 0 and db.query(Lesion).count() == 0 and db.query(UsuarioObjetivo).count() == 0
    assert db.query(IntentoLogin).count() == 0
    assert client.get("/api/auth/me", headers=h).status_code == 401
    assert client.post("/api/auth/login", json={"email": "borrar@pulsegym.app", "password": PASSWORD}).status_code == 401

    confirmacion = correo.BUZON_DE_PRUEBA[-1]
    assert confirmacion["para"] == "borrar@pulsegym.app" and "eliminados" in confirmacion["texto"]


def test_eliminar_la_cuenta_requiere_sesion(client):
    assert client.delete("/api/cuenta").status_code == 401
