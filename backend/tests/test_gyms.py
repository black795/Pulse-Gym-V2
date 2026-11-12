"""PG-06 (mis gyms), PG-13 (máquina malograda o retirada) y PG-14 (implementos)."""
from pathlib import Path

from app.models import Gym
from app.services import gym_service
from tests.conftest import imagen


def _agregar(client, h, gym_id, codigo="PRENSA_45") -> dict:
    """Atajo: sube una foto y la confirma como `codigo`. Devuelve la fila del inventario."""
    foto = client.post(f"/api/gyms/{gym_id}/fotos", files={"archivo": ("m.jpg", imagen(), "image/jpeg")}, headers=h).json()
    r = client.post(f"/api/fotos/{foto['id']}/confirmar", json={"codigo": codigo, "origen": "manual"}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["gym_maquina"]


# ---------------- PG-06 ----------------
def test_un_usuario_puede_tener_varios_gyms_y_arrancan_vacios(client, registrar):
    h = registrar()
    a = client.post("/api/gyms", json={"nombre": "Gym Centro", "ubicacion": "Av. Busch 123"}, headers=h)
    b = client.post("/api/gyms", json={"nombre": "Mi casa"}, headers=h)
    assert a.status_code == b.status_code == 201
    assert a.json()["ubicacion"] == "Av. Busch 123" and b.json()["ubicacion"] is None
    datos = client.get("/api/gyms", headers=h).json()
    assert {g["nombre"] for g in datos["gyms"]} == {"Gym Centro", "Mi casa"} and datos["maximo"] == 5
    detalle = client.get(f"/api/gyms/{a.json()['id']}", headers=h).json()
    assert detalle["inventario"] == [] and detalle["maquinas"] == 0


def test_nombre_obligatorio(client, registrar):
    h = registrar()
    assert client.post("/api/gyms", json={"nombre": "   "}, headers=h).status_code == 422
    assert client.post("/api/gyms", json={}, headers=h).json()["detail"] == "El nombre es obligatorio."


def test_no_permite_dos_gyms_con_el_mismo_nombre(client, gym, registrar):
    h, _ = gym("Gym Centro")
    r = client.post("/api/gyms", json={"nombre": "  gym   centro "}, headers=h)
    assert r.status_code == 409 and r.json()["codigo"] == "gym_duplicado"
    # Otro usuario sí puede usar ese nombre.
    gym("Gym Centro", h=registrar("otro@pulsegym.app"))


def test_maximo_5_gyms(client, registrar):
    h = registrar()
    for i in range(5):
        assert client.post("/api/gyms", json={"nombre": f"Gym {i}"}, headers=h).status_code == 201
    r = client.post("/api/gyms", json={"nombre": "Gym 6"}, headers=h)
    assert r.status_code == 400 and r.json()["codigo"] == "limite_gyms"


def test_renombrar_sin_chocar_con_otro_gym(client, gym):
    h, gid = gym("Gym Centro")
    client.post("/api/gyms", json={"nombre": "Mi casa"}, headers=h)
    assert client.patch(f"/api/gyms/{gid}", json={"nombre": "Gym Norte"}, headers=h).json()["nombre"] == "Gym Norte"
    assert client.patch(f"/api/gyms/{gid}", json={"nombre": "mi casa"}, headers=h).status_code == 409
    assert client.patch(f"/api/gyms/{gid}", json={"ubicacion": "Calle 5"}, headers=h).json()["ubicacion"] == "Calle 5"


def test_se_recuerda_el_ultimo_gym_usado(client, gym):
    h, a = gym("Gym A")
    b = client.post("/api/gyms", json={"nombre": "Gym B"}, headers=h).json()["id"]
    client.post(f"/api/gyms/{a}/usar", headers=h)
    client.post(f"/api/gyms/{b}/usar", headers=h)
    lista = client.get("/api/gyms", headers=h).json()["gyms"]
    assert lista[0]["id"] == b and lista[0]["es_ultimo_usado"] and not lista[1]["es_ultimo_usado"]


def test_eliminar_un_gym_borra_su_inventario_y_sus_fotos(client, gym, db):
    from app.services import fotos_storage

    h, gid = gym()
    gm = _agregar(client, h, gid)
    archivo = fotos_storage.ruta(db.get(Gym, gid).fotos[0].archivo)
    assert archivo.exists()
    assert client.delete(f"/api/gyms/{gid}", headers=h).status_code == 204
    assert client.get(f"/api/gyms/{gid}", headers=h).status_code == 404
    assert not archivo.exists()
    assert gm["id"]


def test_eliminar_gym_mantiene_204_y_continua_si_falla_una_foto(client, gym, db, monkeypatch):
    from app.services import fotos_storage

    h, gid = gym()
    _agregar(client, h, gid, "PRENSA_45")
    _agregar(client, h, gid, "SMITH")
    archivos = [fotos_storage.ruta(f.archivo) for f in db.get(Gym, gid).fotos]
    assert len(archivos) == 2
    unlink = Path.unlink

    def borrar_con_fallo(self, *args, **kwargs):
        if self == archivos[0]:
            raise PermissionError("fallo de prueba")
        return unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", borrar_con_fallo)
    assert client.delete(f"/api/gyms/{gid}", headers=h).status_code == 204
    assert client.get(f"/api/gyms/{gid}", headers=h).status_code == 404
    assert archivos[0].exists()
    assert not archivos[1].exists()


def test_no_se_ve_ni_se_toca_el_gym_de_otro(client, gym, registrar):
    _, gid = gym()
    otro = registrar("otro@pulsegym.app")
    assert client.get(f"/api/gyms/{gid}", headers=otro).status_code == 404
    assert client.delete(f"/api/gyms/{gid}", headers=otro).status_code == 404
    assert client.post(f"/api/gyms/{gid}/fotos", files={"archivo": ("m.jpg", imagen(), "image/jpeg")}, headers=otro).status_code == 404


# ---------------- PG-13 ----------------
def test_estados_y_fecha_de_cada_cambio(client, gym):
    h, gid = gym()
    gm = _agregar(client, h, gid)
    assert gm["estado"] == "disponible"
    url = f"/api/gyms/{gid}/maquinas/{gm['id']}"
    assert client.patch(url, json={"estado": "malograda"}, headers=h).json()["estado"] == "malograda"
    assert client.patch(url, json={"estado": "disponible"}, headers=h).json()["estado"] == "disponible"
    r = client.patch(url, json={"estado": "retirada"}, headers=h).json()
    assert [x["estado"] for x in r["historial_estados"]] == ["disponible", "malograda", "disponible", "retirada"]
    assert all(x["fecha"] for x in r["historial_estados"])
    assert client.patch(url, json={"estado": "rota"}, headers=h).status_code == 422


def test_malogradas_y_retiradas_no_cuentan_como_disponibles(client, gym):
    h, gid = gym()
    prensa = _agregar(client, h, gid, "PRENSA_45")
    _agregar(client, h, gid, "HACK_SQUAT")
    smith = _agregar(client, h, gid, "SMITH")
    client.patch(f"/api/gyms/{gid}/maquinas/{prensa['id']}", json={"estado": "malograda"}, headers=h)
    client.patch(f"/api/gyms/{gid}/maquinas/{smith['id']}", json={"estado": "retirada"}, headers=h)
    assert client.get(f"/api/gyms/{gid}/disponibles", headers=h).json() == ["HACK_SQUAT"]
    assert client.get(f"/api/gyms/{gid}", headers=h).json()["maquinas"] == 2  # la retirada no se cuenta


def test_alternativas_usan_lo_disponible_en_el_gym(client, gym):
    h, gid = gym()
    ejercicios = client.get("/api/catalogo/ejercicios?maquina=PRENSA_45", headers=h).json()
    eid = ejercicios[0]["id"]
    alts = client.get(f"/api/catalogo/ejercicios/{eid}/alternativas?gym_id={gid}&limite=100", headers=h).json()
    # Gym vacío: solo quedan ejercicios sin equipo.
    assert alts and all(a["categoria_equipo"] == "sin_equipo" for a in alts)


# ---------------- PG-14 ----------------
def test_lista_de_implementos(client, registrar):
    codigos = [i["codigo"] for i in client.get("/api/implementos", headers=registrar()).json()]
    assert codigos == ["mancuernas", "barra", "discos", "banco_plano", "banco_inclinable", "rack",
                       "barra_dominadas", "kettlebell", "bandas", "colchoneta"]


def test_marcar_implementos_y_peso_maximo_de_mancuernas(client, gym):
    h, gid = gym()
    r = client.put(f"/api/gyms/{gid}/implementos", json={"implementos": ["mancuernas", "banco_plano"], "mancuernas_max_kg": 30}, headers=h)
    assert r.status_code == 200
    d = r.json()
    assert [i["codigo"] for i in d["lista_implementos"] if i["marcado"]] == ["mancuernas", "banco_plano"]
    assert d["mancuernas_max_kg"] == 30
    assert set(client.get(f"/api/gyms/{gid}/disponibles", headers=h).json()) == {"MANCUERNAS", "BANCO_PLANO"}

    # Se pueden editar en cualquier momento; sin mancuernas, el peso máximo se borra.
    d = client.put(f"/api/gyms/{gid}/implementos", json={"implementos": ["kettlebell"], "mancuernas_max_kg": 30}, headers=h).json()
    assert d["mancuernas_max_kg"] is None and d["implementos"] == 1
    assert client.put(f"/api/gyms/{gid}/implementos", json={"implementos": ["trampolin"]}, headers=h).status_code == 400


def test_los_ejercicios_con_peso_corporal_siempre_estan_disponibles(client, gym):
    h, gid = gym()  # gym vacío, sin implementos
    sin_equipo = client.get("/api/catalogo/ejercicios?categoria=sin_equipo", headers=h).json()
    eid = next(e["id"] for e in client.get("/api/catalogo/ejercicios?categoria=maquina", headers=h).json())
    alts = client.get(f"/api/catalogo/ejercicios/{eid}/alternativas?gym_id={gid}&limite=100", headers=h).json()
    assert sin_equipo and any(a["nivel_busqueda"] == 3 for a in alts)


def test_agregar_maquina_directo_del_catalogo(client, gym):
    h, gid = gym("Gym Hierro")
    r = client.post(f"/api/gyms/{gid}/maquinas", json={"codigo": "PENDULO"}, headers=h)
    assert r.status_code == 201
    assert r.json()["maquina"]["codigo"] == "PENDULO"
    assert r.json()["estado"] == "disponible"

    # No permite duplicar si ya está activa
    r2 = client.post(f"/api/gyms/{gid}/maquinas", json={"codigo": "PENDULO"}, headers=h)
    assert r2.status_code == 409 and r2.json()["codigo"] == "ya_en_inventario"


def test_lista_sin_gyms_no_consulta_ultimo_usado(client, registrar, monkeypatch):
    h = registrar()
    consultas = []
    monkeypatch.setattr(gym_service, "_ultimo_usado_id", lambda *args: consultas.append(args))

    respuesta = client.get("/api/gyms", headers=h)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"gyms": [], "maximo": 5}
    assert consultas == []


def test_lista_sin_uso_previo_conserva_campos_y_orden(client, registrar, monkeypatch):
    h = registrar()
    creados = [client.post("/api/gyms", json={"nombre": nombre}, headers=h).json()
               for nombre in ("Gym A", "Gym B", "Gym C")]
    consultas = []
    original = gym_service._ultimo_usado_id

    def consultar(db, usuario):
        consultas.append(1)
        return original(db, usuario)

    monkeypatch.setattr(gym_service, "_ultimo_usado_id", consultar)
    respuesta = client.get("/api/gyms", headers=h)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"gyms": creados, "maximo": 5}
    assert all(g["ultimo_uso_at"] is None and g["es_ultimo_usado"] is False for g in creados)
    assert consultas == []


def test_lista_con_ultimo_uso_no_repite_consultas(client, registrar, monkeypatch):
    h = registrar()
    a = client.post("/api/gyms", json={"nombre": "Gym A"}, headers=h).json()
    b = client.post("/api/gyms", json={"nombre": "Gym B"}, headers=h).json()
    usado = client.post(f"/api/gyms/{b['id']}/usar", headers=h).json()
    consultas = []
    monkeypatch.setattr(gym_service, "_ultimo_usado_id", lambda *args: consultas.append(args))

    respuesta = client.get("/api/gyms", headers=h)

    assert respuesta.status_code == 200
    assert respuesta.json() == {"gyms": [usado, a], "maximo": 5}
    assert usado["es_ultimo_usado"] is True and a["es_ultimo_usado"] is False
    assert consultas == []


def test_detalle_consulta_ultimo_y_conserva_campos_resumen(client, gym, monkeypatch):
    h, gid = gym()
    resumen = client.post(f"/api/gyms/{gid}/usar", headers=h).json()
    consultas = []
    original = gym_service._ultimo_usado_id

    def consultar(db, usuario):
        consultas.append(1)
        return original(db, usuario)

    monkeypatch.setattr(gym_service, "_ultimo_usado_id", consultar)
    respuesta = client.get(f"/api/gyms/{gid}", headers=h)

    assert respuesta.status_code == 200
    detalle = respuesta.json()
    assert {campo: detalle[campo] for campo in resumen} == resumen
    assert detalle["inventario"] == []
    assert len(consultas) == 1
