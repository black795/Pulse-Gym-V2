import os
import tempfile

# Variables de entorno ANTES de importar la app (usa una base de datos temporal).
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ.update(
    DATABASE_URL=f"sqlite:///{_tmp.name}",
    SECRET_KEY="clave-de-pruebas-clave-de-pruebas-1234567890",
    SEED_DEMO="true",
    SEED_DATOS_COMPLETOS="false",
    DEMO_EMAIL="demo@pulsegym.app",
    DEMO_PASSWORD="Pulse2026!",
    BCRYPT_ROUNDS="4",  # rápido en pruebas
    ENTORNO="desarrollo",
    CORREO_MODO="consola",
    URL_APP="http://app.test",
    FOTOS_DIR=tempfile.mkdtemp(prefix="pulse-fotos-"),
    IA_PROVEEDOR="simulada",  # las pruebas nunca llaman a internet
    GEMINI_API_KEY="",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import correo  # noqa: E402

PASSWORD = "Pulse2026!"


@pytest.fixture()
def client():
    """Cada prueba empieza con la base de datos limpia (catálogo y cuenta demo incluidos)."""
    Base.metadata.drop_all(engine)
    correo.BUZON_DE_PRUEBA.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(client):
    with SessionLocal() as s:
        yield s


@pytest.fixture()
def registrar(client):
    """registrar('ana@x.com') → encabezados con el token de esa cuenta nueva."""

    def _registrar(email: str = "ana@pulsegym.app", nombre: str = "Ana Pérez", password: str = PASSWORD) -> dict:
        r = client.post("/api/auth/registro", json={"nombre": nombre, "email": email, "password": password})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _registrar


def imagen(color=(120, 130, 140), tamano=(2000, 1500), formato="JPEG", exif_gps=False) -> bytes:
    """Imagen de prueba en memoria. exif_gps=True le pone metadatos de ubicación, como una foto de celular."""
    import io

    from PIL import Image

    img = Image.new("RGB", tamano, color)
    salida = io.BytesIO()
    if exif_gps:
        exif = Image.Exif()
        exif[0x8825] = {1: "S", 2: (16.0, 30.0, 0.0)}  # GPSInfo
        img.save(salida, formato, exif=exif)
    else:
        img.save(salida, formato)
    return salida.getvalue()


@pytest.fixture()
def gym(client, registrar):
    """gym() → (encabezados, id de un gym nuevo)."""

    def _gym(nombre: str = "Gym Centro", h: dict | None = None) -> tuple[dict, int]:
        h = h or registrar()
        r = client.post("/api/gyms", json={"nombre": nombre}, headers=h)
        assert r.status_code == 201, r.text
        return h, r.json()["id"]

    return _gym


@pytest.fixture()
def con_consentimiento(client, registrar):
    """Cuenta nueva que ya aceptó el consentimiento de datos de salud."""

    def _crear(email: str = "ana@pulsegym.app") -> dict:
        h = registrar(email)
        assert client.put("/api/consentimiento", json={"acepta": True}, headers=h).status_code == 200
        return h

    return _crear
