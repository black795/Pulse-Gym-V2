"""PG-07 (foto), PG-08 (reconocimiento IA), PG-09 (confirmar o elegir), PG-12 (sin duplicados), PG-48 (privacidad)."""
import io
import time

import pytest
from PIL import Image

from app.models import FotoMaquina, ReconocimientoIA
from app.services import ia_vision
from tests.conftest import imagen


def _subir(client, h, gid, contenido=None, nombre="m.jpg", tipo="image/jpeg"):
    return client.post(f"/api/gyms/{gid}/fotos", files={"archivo": (nombre, contenido or imagen(), tipo)}, headers=h)


@pytest.fixture()
def ia(monkeypatch):
    """ia({...}) → la IA simulada responde exactamente eso (o lanza ErrorIA si se pasa una excepción)."""

    def _fijar(respuesta):
        def falsa(_img, _catalogo):
            if isinstance(respuesta, Exception):
                raise respuesta
            return "modelo-prueba", respuesta
        monkeypatch.setitem(ia_vision.PROVEEDORES, "simulada", falsa)

    return _fijar


# ---------------- PG-07 ----------------
def test_se_reduce_a_1280px_y_se_quitan_los_metadatos(client, gym, db):
    from app.services import fotos_storage

    h, gid = gym()
    r = _subir(client, h, gid, imagen(tamano=(4000, 3000), exif_gps=True))
    assert r.status_code == 201, r.text
    foto = db.get(FotoMaquina, r.json()["id"])
    guardada = Image.open(fotos_storage.ruta(foto.archivo))
    assert max(guardada.size) == 1280 and guardada.format == "JPEG"
    assert not guardada.getexif()  # sin ubicación GPS


def test_acepta_png_y_rechaza_lo_que_no_es_imagen_o_pesa_mas_de_10mb(client, gym):
    h, gid = gym()
    assert _subir(client, h, gid, imagen(formato="PNG"), "m.png", "image/png").status_code == 201
    r = _subir(client, h, gid, b"esto no es una foto", "m.jpg")
    assert r.status_code == 415 and r.json()["codigo"] == "foto_invalida"
    r = _subir(client, h, gid, b"0" * (10 * 1024 * 1024 + 1))
    assert r.status_code == 413 and r.json()["codigo"] == "foto_muy_grande"


def test_acepta_heic(client, gym):
    pillow_heif = pytest.importorskip("pillow_heif")
    h, gid = gym()
    salida = io.BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (800, 600), (90, 90, 90))).save(salida, format="HEIF")
    assert _subir(client, h, gid, salida.getvalue(), "m.heic", "image/heic").status_code == 201


# ---------------- PG-08 ----------------
def test_la_ia_responde_maquinas_del_catalogo_con_su_confianza(client, gym, ia, db):
    ia({"es_maquina_de_gym": True, "sugerencias": [{"codigo": "HACK_SQUAT", "confianza": 0.62}, {"codigo": "PRENSA_45", "confianza": 0.31}]})
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    r = client.post(f"/api/fotos/{fid}/reconocer", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert [(s["puesto"], s["maquina"]["codigo"], s["confianza"]) for s in d["sugerencias"]] == [(1, "HACK_SQUAT", 0.62), (2, "PRENSA_45", 0.31)]
    assert d["modelo"] == "modelo-prueba" and not d["confianza_alta"] and d["foto"]["estado"] == "opciones_sugeridas"
    # Cada opción trae nombre, foto de referencia y músculo principal (PG-09).
    s = d["sugerencias"][0]["maquina"]
    assert s["nombre"] and s["foto_ref"] and s["musculo_principal"]
    # Cada intento queda guardado: modelo, máquina, confianza y puesto.
    filas = db.query(ReconocimientoIA).filter_by(foto_id=fid).all()
    assert {(f.puesto, f.modelo, f.confianza, f.intento) for f in filas} == {(1, "modelo-prueba", 0.62, 1), (2, "modelo-prueba", 0.31, 1)}


def test_codigos_inventados_por_la_ia_se_descartan(client, gym, ia):
    ia({"es_maquina_de_gym": True, "sugerencias": [
        {"codigo": "MAQUINA_INVENTADA", "confianza": 0.99}, {"codigo": "smith", "confianza": 0.5},
        {"codigo": "SMITH", "confianza": 0.4}, {"codigo": "PEC_DECK", "confianza": 7},
    ]})
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    d = client.post(f"/api/fotos/{fid}/reconocer", headers=h).json()
    # PEC_DECK: confianza 7 → se acota a 1. SMITH aparece una sola vez, con su mejor confianza.
    assert [(s["maquina"]["codigo"], s["confianza"]) for s in d["sugerencias"]] == [("PEC_DECK", 1.0), ("SMITH", 0.5)]


def test_si_no_es_una_maquina_pide_otra_foto(client, gym, ia):
    ia({"es_maquina_de_gym": False, "sugerencias": [{"codigo": "SMITH", "confianza": 0.2}]})
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    d = client.post(f"/api/fotos/{fid}/reconocer", headers=h).json()
    assert d["es_maquina_de_gym"] is False and d["sugerencias"] == [] and d["foto"]["estado"] == "no_es_maquina"


def test_si_la_ia_falla_responde_503_y_se_puede_reintentar(client, gym, ia, db):
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    ia(ia_vision.ErrorIA("La IA tardó más de 15 segundos."))
    r = client.post(f"/api/fotos/{fid}/reconocer", headers=h)
    assert r.status_code == 503 and r.json()["codigo"] == "ia_fallo" and "a mano" in r.json()["detail"]
    db.expire_all()
    assert db.get(FotoMaquina, fid).estado == "error_ia"

    ia({"es_maquina_de_gym": True, "sugerencias": [{"codigo": "SMITH", "confianza": 0.9}]})
    d = client.post(f"/api/fotos/{fid}/reconocer", headers=h).json()
    assert d["confianza_alta"] and d["foto"]["estado"] == "reconocida_alta"
    db.expire_all()
    f = db.get(FotoMaquina, fid)
    assert f.ia_intentos == 2 and [r.intento for r in f.reconocimientos] == [2]


def test_respuesta_rara_de_la_ia_no_rompe_nada():
    es, sug, desc = ia_vision.limpiar_respuesta({"sugerencias": ["x", {"codigo": None}, {"codigo": "SMITH", "confianza": "alta"}]}, {"SMITH"})
    assert es is False and sug == [("SMITH", 0.0)] and desc == 2
    with pytest.raises(ia_vision.ErrorIA):
        ia_vision.limpiar_respuesta(["no", "es", "un", "objeto"], {"SMITH"})  # type: ignore[arg-type]


def test_la_ia_simulada_sugiere_maquinas_reales_del_catalogo(client, gym):
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    d = client.post(f"/api/fotos/{fid}/reconocer", headers=h).json()
    codigos = {m["codigo"] for m in client.get("/api/catalogo/maquinas", headers=h).json()}
    assert d["modelo"] == "simulada" and len(d["sugerencias"]) == 3
    assert all(s["maquina"]["codigo"] in codigos for s in d["sugerencias"])


# ---------------- PG-09 ----------------
def test_confianza_alta_desde_085(client, gym, ia):
    h, gid = gym()
    ia({"es_maquina_de_gym": True, "sugerencias": [{"codigo": "SMITH", "confianza": 0.85}]})
    assert client.post(f"/api/fotos/{_subir(client, h, gid).json()['id']}/reconocer", headers=h).json()["confianza_alta"]
    ia({"es_maquina_de_gym": True, "sugerencias": [{"codigo": "SMITH", "confianza": 0.84}]})
    assert not client.post(f"/api/fotos/{_subir(client, h, gid).json()['id']}/reconocer", headers=h).json()["confianza_alta"]


def test_nada_entra_al_inventario_sin_confirmar_y_se_registra_la_eleccion(client, gym, ia, db):
    ia({"es_maquina_de_gym": True, "sugerencias": [{"codigo": "HACK_SQUAT", "confianza": 0.6}, {"codigo": "PRENSA_45", "confianza": 0.3}]})
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    client.post(f"/api/fotos/{fid}/reconocer", headers=h)
    assert client.get(f"/api/gyms/{gid}", headers=h).json()["inventario"] == []  # la IA sola no agrega nada

    r = client.post(f"/api/fotos/{fid}/confirmar", json={"codigo": "PRENSA_45", "origen": "sugerencia"}, headers=h)
    assert r.status_code == 200 and r.json()["accion"] == "agregada"
    inv = client.get(f"/api/gyms/{gid}", headers=h).json()["inventario"]
    assert [m["maquina"]["codigo"] for m in inv] == ["PRENSA_45"] and inv[0]["foto_url"]
    db.expire_all()
    f = db.get(FotoMaquina, fid)
    assert (f.eleccion, f.elegida_puesto, f.estado) == ("sugerencia", 2, "confirmada")  # eligió la 2.ª opción


def test_buscar_a_mano_por_nombre_o_musculo(client, gym):
    h, gid = gym()
    por_nombre = client.get("/api/catalogo/maquinas?q=prensa", headers=h).json()
    assert {m["codigo"] for m in por_nombre} >= {"PRENSA_45", "PRENSA_HORIZONTAL"}
    assert client.get("/api/catalogo/maquinas?q=LEG PRESS", headers=h).json()  # otros nombres, sin importar mayúsculas
    assert any(m["codigo"] == "EXT_CUADRICEPS" for m in client.get("/api/catalogo/maquinas?q=cuadriceps", headers=h).json())  # sin tilde
    grupo = por_nombre[0]["musculo_principal"]
    assert grupo
    grupos = {g["nombre"]: g["codigo"] for g in client.get("/api/catalogo/grupos-musculares", headers=h).json()}
    por_musculo = client.get(f"/api/catalogo/maquinas?grupo={grupos[grupo]}", headers=h).json()
    assert por_musculo and all(m["musculo_principal"] == grupo for m in por_musculo)

    fid = _subir(client, h, gid).json()["id"]
    r = client.post(f"/api/fotos/{fid}/confirmar", json={"codigo": "EXT_CUADRICEPS", "origen": "manual"}, headers=h)
    assert r.status_code == 200  # se puede elegir a mano sin haber llamado a la IA


def test_ninguna_es_queda_para_la_busqueda_en_internet(client, gym, db):
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    assert client.post(f"/api/fotos/{fid}/ninguna", headers=h).json()["estado"] == "busqueda_web"
    db.expire_all()
    assert db.get(FotoMaquina, fid).eleccion == "ninguna"


def test_maquina_fuera_del_catalogo_no_se_puede_confirmar(client, gym):
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    assert client.post(f"/api/fotos/{fid}/confirmar", json={"codigo": "NO_EXISTE", "origen": "manual"}, headers=h).status_code == 404


# ---------------- PG-12 ----------------
def test_si_la_maquina_ya_esta_avisa_y_no_la_duplica(client, gym, db):
    from app.services import fotos_storage

    h, gid = gym()
    f1 = _subir(client, h, gid).json()["id"]
    client.post(f"/api/fotos/{f1}/confirmar", json={"codigo": "SMITH", "origen": "manual"}, headers=h)
    archivo_viejo = fotos_storage.ruta(db.get(FotoMaquina, f1).archivo)

    f2 = _subir(client, h, gid, imagen(color=(10, 200, 10))).json()["id"]
    r = client.post(f"/api/fotos/{f2}/confirmar", json={"codigo": "SMITH", "origen": "manual"}, headers=h)
    assert r.status_code == 409 and r.json()["codigo"] == "ya_en_inventario"
    assert len(client.get(f"/api/gyms/{gid}", headers=h).json()["inventario"]) == 1

    # Puede actualizar la foto de la existente: la vieja se borra.
    r = client.post(f"/api/fotos/{f2}/confirmar", json={"codigo": "SMITH", "origen": "manual", "reemplazar_foto": True}, headers=h)
    assert r.status_code == 200 and r.json()["accion"] == "foto_actualizada"
    assert len(client.get(f"/api/gyms/{gid}", headers=h).json()["inventario"]) == 1
    assert not archivo_viejo.exists()


def test_la_base_de_datos_impide_duplicados(db, client, gym):
    from sqlalchemy.exc import IntegrityError

    from app.models import GymMaquina, MaquinaCatalogo

    _, gid = gym()
    mid = db.query(MaquinaCatalogo).filter_by(codigo="SMITH").one().id
    db.add_all([GymMaquina(gym_id=gid, maquina_id=mid, historial_estados=[]), GymMaquina(gym_id=gid, maquina_id=mid, historial_estados=[])])
    with pytest.raises(IntegrityError):
        db.commit()


def test_eliminar_una_maquina_agregada_por_error(client, gym):
    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    gm = client.post(f"/api/fotos/{fid}/confirmar", json={"codigo": "SMITH", "origen": "manual"}, headers=h).json()["gym_maquina"]
    assert client.delete(f"/api/gyms/{gid}/maquinas/{gm['id']}", headers=h).status_code == 204
    assert client.get(f"/api/gyms/{gid}", headers=h).json()["inventario"] == []


# ---------------- PG-48 ----------------
def test_la_foto_solo_se_ve_con_el_enlace_temporal_y_solo_el_dueno_lo_recibe(client, gym, registrar):
    h, gid = gym()
    foto = _subir(client, h, gid).json()
    url = foto["url"]
    assert url.startswith(f"/api/fotos/{foto['id']}/imagen?exp=")
    r = client.get(url)
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and "private" in r.headers["cache-control"]

    # Firma alterada, foto ajena con la firma de otra, o enlace vencido → no se ve.
    assert client.get(url[:-4] + "0000").status_code == 403
    assert client.get(url.replace(f"/fotos/{foto['id']}/", f"/fotos/{foto['id'] + 1}/")).status_code == 403
    vencido = f"/api/fotos/{foto['id']}/imagen?exp={int(time.time()) - 1}&firma=" + url.split("firma=")[1]
    assert client.get(vencido).status_code == 403
    # Otro usuario no puede reconocer, confirmar ni descartar la foto.
    otro = registrar("otro@pulsegym.app")
    assert client.post(f"/api/fotos/{foto['id']}/reconocer", headers=otro).status_code == 404
    assert client.delete(f"/api/fotos/{foto['id']}", headers=otro).status_code == 404


def test_el_enlace_dura_maximo_una_hora(client, gym):
    h, gid = gym()
    url = _subir(client, h, gid).json()["url"]
    exp = int(url.split("exp=")[1].split("&")[0])
    assert exp - time.time() <= 3600


def test_al_borrar_la_cuenta_se_borran_sus_fotos(client, gym, db):
    from app.services import fotos_storage

    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    archivo = fotos_storage.ruta(db.get(FotoMaquina, fid).archivo)
    assert archivo.exists()
    assert client.delete("/api/cuenta", headers=h).status_code == 204
    assert not archivo.exists()


def test_descartar_una_foto_borra_el_archivo(client, gym, db):
    from app.services import fotos_storage

    h, gid = gym()
    fid = _subir(client, h, gid).json()["id"]
    archivo = fotos_storage.ruta(db.get(FotoMaquina, fid).archivo)
    assert client.delete(f"/api/fotos/{fid}", headers=h).status_code == 204
    assert not archivo.exists()
