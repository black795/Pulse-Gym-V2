"""PG-01: registro, inicio de sesión, bloqueo, sesión de 30 días y recuperación de contraseña."""
from datetime import timedelta

import jwt

from app.core.config import get_settings
from app.db.base import ahora
from app.models import IntentoLogin, RecuperacionPassword, Usuario
from app.services import correo
from tests.conftest import PASSWORD


def registro(client, **extra):
    datos = {"nombre": "Ana Pérez", "email": "ana@pulsegym.app", "password": PASSWORD, **extra}
    return client.post("/api/auth/registro", json=datos)


def login(client, email="ana@pulsegym.app", password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------------- registro
def test_registro_crea_cuenta_y_devuelve_sesion(client):
    r = registro(client)
    assert r.status_code == 201
    u = r.json()["usuario"]
    assert u["email"] == "ana@pulsegym.app" and u["consentimiento_estado"] == "pendiente"
    assert u["perfil_completo"] is False
    assert "rol" not in u and "permisos" not in u  # un único rol: no se expone ninguno


def test_registro_rechaza_intentar_enviar_un_rol(client):
    assert registro(client, rol="administrador").status_code == 422


def test_registro_valida_correo_y_contrasena_en_espanol(client):
    r = registro(client, email="no-es-correo")
    assert r.status_code == 422 and r.json()["detail"] == "El correo no es válido."
    r = registro(client, password="corta1")
    assert r.status_code == 422 and "mínimo 8" in r.json()["detail"]
    r = registro(client, password="soloLetrasAqui")
    assert r.status_code == 422 and "una letra y un número" in r.json()["detail"]
    r = registro(client, password="12345678")
    assert r.status_code == 422 and "una letra y un número" in r.json()["detail"]


def test_correo_repetido_da_mensaje_claro_y_ofrece_iniciar_sesion(client):
    registro(client)
    r = registro(client, email="ANA@pulsegym.app")  # mayúsculas: es el mismo correo
    assert r.status_code == 409
    assert r.json()["codigo"] == "correo_existente" and "Inicia sesión" in r.json()["detail"]


def test_la_contrasena_se_guarda_cifrada(client, db):
    registro(client)
    h = db.query(Usuario).filter_by(email="ana@pulsegym.app").one().password_hash
    assert PASSWORD not in h and h.startswith("$2")  # bcrypt


# ---------------- login
def test_login_correcto_y_me(client):
    registro(client)
    r = login(client)
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=h).json()["email"] == "ana@pulsegym.app"


def test_credenciales_incorrectas_dan_el_mismo_error_sin_revelar_cual_fallo(client):
    registro(client)
    mala_pass = login(client, password="OtraClave123")
    sin_correo = login(client, email="nadie@pulsegym.app")
    assert mala_pass.status_code == sin_correo.status_code == 401
    assert mala_pass.json() == sin_correo.json()


def test_la_sesion_dura_30_dias(client):
    r = registro(client).json()
    assert r["expira_en_dias"] == 30
    datos = jwt.decode(r["access_token"], get_settings().secret_key, algorithms=["HS256"])
    assert datos["exp"] - datos["iat"] == 30 * 24 * 3600


def test_sin_token_o_con_token_falso_da_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer falso"}).status_code == 401


# ---------------- bloqueo por intentos
def test_cinco_intentos_fallidos_bloquean_15_minutos_incluso_con_la_clave_correcta(client, db):
    registro(client)
    for _ in range(4):
        assert login(client, password="Incorrecta1").status_code == 401
    quinto = login(client, password="Incorrecta1")
    assert quinto.status_code == 429 and quinto.json()["codigo"] == "login_bloqueado"

    # Aunque ahora acierte la contraseña, sigue bloqueado.
    assert login(client).status_code == 429

    # Pasan los 15 minutos → vuelve a poder entrar.
    intento = db.get(IntentoLogin, "ana@pulsegym.app")
    assert intento.bloqueado_hasta - ahora() <= timedelta(minutes=15)
    intento.bloqueado_hasta = ahora() - timedelta(seconds=1)
    db.commit()
    assert login(client).status_code == 200


def test_un_correo_inexistente_tambien_se_bloquea_igual(client):
    for _ in range(4):
        assert login(client, email="fantasma@pulsegym.app").status_code == 401
    assert login(client, email="fantasma@pulsegym.app").status_code == 429


def test_un_login_correcto_reinicia_el_contador(client):
    registro(client)
    for _ in range(3):
        login(client, password="Incorrecta1")
    assert login(client).status_code == 200
    for _ in range(4):  # si no se hubiera reiniciado, el 2.º fallo ya bloquearía
        assert login(client, password="Incorrecta1").status_code == 401


# ---------------- recuperación de contraseña
def _token_del_correo() -> str:
    texto = correo.BUZON_DE_PRUEBA[-1]["texto"]
    enlace = next(l for l in texto.splitlines() if l.startswith("http://app.test/restablecer?token="))
    return enlace.split("token=")[1]


def test_recuperar_responde_igual_exista_o_no_el_correo(client):
    registro(client)
    a = client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    n_correos = len(correo.BUZON_DE_PRUEBA)
    b = client.post("/api/auth/recuperar", json={"email": "nadie@pulsegym.app"})
    assert a.status_code == b.status_code == 200 and a.json() == b.json()
    assert n_correos == 1 and len(correo.BUZON_DE_PRUEBA) == 1  # a la cuenta inexistente no se le envió nada


def test_restablecer_cambia_la_clave_y_el_enlace_sirve_una_sola_vez(client):
    registro(client)
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    token = _token_del_correo()

    r = client.post("/api/auth/restablecer", json={"token": token, "password": "NuevaClave456"})
    assert r.status_code == 200
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="NuevaClave456").status_code == 200

    otra_vez = client.post("/api/auth/restablecer", json={"token": token, "password": "OtraMas789xx"})
    assert otra_vez.status_code == 400 and otra_vez.json()["codigo"] == "enlace_invalido"


def test_el_enlace_vence_a_los_30_minutos(client, db):
    registro(client)
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    rec = db.query(RecuperacionPassword).one()
    assert timedelta(minutes=29) < rec.expira_at - rec.created_at <= timedelta(minutes=30)

    rec.expira_at = ahora() - timedelta(seconds=1)
    db.commit()
    r = client.post("/api/auth/restablecer", json={"token": _token_del_correo(), "password": "NuevaClave456"})
    assert r.status_code == 400


def test_un_enlace_nuevo_anula_el_anterior(client):
    registro(client)
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    viejo = _token_del_correo()
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    nuevo = _token_del_correo()
    assert client.post("/api/auth/restablecer", json={"token": viejo, "password": "NuevaClave456"}).status_code == 400
    assert client.post("/api/auth/restablecer", json={"token": nuevo, "password": "NuevaClave456"}).status_code == 200


def test_en_la_base_solo_queda_el_hash_del_enlace(client, db):
    registro(client)
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    assert _token_del_correo() != db.query(RecuperacionPassword).one().token_hash
    assert _token_del_correo() not in db.query(RecuperacionPassword).one().token_hash


def test_restablecer_cierra_las_sesiones_abiertas_en_otros_celulares(client):
    sesion_vieja = {"Authorization": f"Bearer {registro(client).json()['access_token']}"}
    assert client.get("/api/auth/me", headers=sesion_vieja).status_code == 200
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    client.post("/api/auth/restablecer", json={"token": _token_del_correo(), "password": "NuevaClave456"})
    assert client.get("/api/auth/me", headers=sesion_vieja).status_code == 401


def test_recuperar_la_clave_desbloquea_la_cuenta(client):
    registro(client)
    for _ in range(5):
        login(client, password="Incorrecta1")
    assert login(client).status_code == 429
    client.post("/api/auth/recuperar", json={"email": "ana@pulsegym.app"})
    client.post("/api/auth/restablecer", json={"token": _token_del_correo(), "password": "NuevaClave456"})
    assert login(client, password="NuevaClave456").status_code == 200
