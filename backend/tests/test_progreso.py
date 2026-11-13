"""Sprint 5 (parcial): PG-38 constancia/racha y PG-46 historial de sesiones."""
from datetime import date, datetime, timedelta

from app.db.base import ahora
from app.models import SesionEntreno
from app.services.progreso_service import calcular_rachas

HOY = date(2026, 11, 12)  # jueves


def d(atras: int) -> date:
    return HOY - timedelta(days=atras)


# ---------------- Racha: función pura ----------------
def test_sin_sesiones_no_hay_racha():
    assert calcular_rachas(set(), HOY) == (0, 0)


def test_racha_incluye_hoy():
    assert calcular_rachas({d(0), d(1), d(2)}, HOY) == (3, 3)


def test_racha_sigue_viva_si_el_ultimo_fue_ayer():
    assert calcular_rachas({d(1), d(2)}, HOY) == (2, 2)


def test_racha_se_pierde_con_un_dia_sin_entrenar():
    assert calcular_rachas({d(2), d(3), d(4)}, HOY) == (0, 3)


def test_mejor_racha_pasada_es_mayor_que_la_actual():
    assert calcular_rachas({d(0), d(10), d(11), d(12), d(13)}, HOY) == (1, 4)


def test_fechas_futuras_no_inflan_la_racha_actual():
    assert calcular_rachas({d(0), HOY + timedelta(days=1)}, HOY)[0] == 1


# ---------------- Endpoints ----------------
def sesion(db, usuario_id, fecha, estado="completa", asistencia=True, **extra):
    inicio = datetime.combine(fecha, datetime.min.time()).replace(hour=18)
    s = SesionEntreno(
        usuario_id=usuario_id, dia_semana="lunes", enfoque="Cuerpo completo A", fecha=fecha, inicio_at=inicio,
        fin_at=inicio + timedelta(minutes=50), estado=estado, cuenta_asistencia=asistencia, gym_nombre="Mi gym", **extra,
    )
    db.add(s)
    db.commit()
    return s


def mi_id(client, h):
    return client.get("/api/auth/me", headers=h).json()["id"]


def constancia(client, h, fecha=HOY):
    r = client.get("/api/progreso/constancia", params={"fecha": fecha.isoformat()}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_exige_sesion_iniciada(client):
    assert client.get("/api/progreso/constancia").status_code == 401
    assert client.get("/api/progreso/historial").status_code == 401


def test_constancia_vacia(client, registrar):
    assert constancia(client, registrar()) == {
        "racha_actual": 0, "mejor_racha": 0, "entreno_hoy": False, "sesiones_semana": 0, "sesiones_mes": 0,
        "ultima_sesion": None,
    }


def test_constancia_cuenta_semana_mes_y_racha(client, registrar, db):
    h = registrar()
    uid = mi_id(client, h)
    for atras in (0, 1, 2):  # jueves, miércoles, martes de esta semana
        sesion(db, uid, d(atras))
    sesion(db, uid, date(2026, 11, 1))  # este mes, otra semana
    sesion(db, uid, date(2026, 10, 31))  # mes anterior
    c = constancia(client, h)
    assert c["racha_actual"] == 3 and c["entreno_hoy"] is True and c["ultima_sesion"] == HOY.isoformat()
    assert c["sesiones_semana"] == 3  # lunes 9 a domingo 15
    assert c["sesiones_mes"] == 4


def test_la_parcial_no_cuenta_para_la_constancia(client, registrar, db):
    h = registrar()
    uid = mi_id(client, h)
    sesion(db, uid, d(0), estado="parcial", asistencia=False)
    c = constancia(client, h)
    assert c["racha_actual"] == 0 and c["sesiones_semana"] == 0 and c["entreno_hoy"] is False


def test_la_constancia_es_por_usuario(client, registrar, db):
    ana, beto = registrar("ana@x.com"), registrar("beto@x.com", nombre="Beto Díaz")
    sesion(db, mi_id(client, ana), d(0))
    assert constancia(client, ana)["racha_actual"] == 1
    assert constancia(client, beto)["racha_actual"] == 0


def test_diciembre_a_enero_el_mes_siguiente_se_calcula(client, registrar, db):
    h = registrar()
    uid = mi_id(client, h)
    sesion(db, uid, date(2026, 12, 31))
    sesion(db, uid, date(2027, 1, 1))
    assert constancia(client, h, date(2026, 12, 31))["sesiones_mes"] == 1


def test_historial_ordenado_con_completas_y_parciales(client, registrar, db):
    h = registrar()
    uid = mi_id(client, h)
    sesion(db, uid, d(5))
    sesion(db, uid, d(1), estado="parcial", asistencia=False)
    sesion(db, uid, d(3))
    r = client.get("/api/progreso/historial", headers=h)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 3
    assert [s["fecha"] for s in cuerpo["sesiones"]] == [d(1).isoformat(), d(3).isoformat(), d(5).isoformat()]
    primera = cuerpo["sesiones"][0]
    assert primera["estado"] == "parcial" and primera["cuenta_asistencia"] is False
    assert primera["duracion_seg"] == 3000 and primera["gym_nombre"] == "Mi gym"


def test_historial_no_incluye_en_curso_ni_sesiones_ajenas(client, registrar, db):
    ana, beto = registrar("ana@x.com"), registrar("beto@x.com", nombre="Beto Díaz")
    sesion(db, mi_id(client, ana), d(2))
    en_curso = sesion(db, mi_id(client, ana), d(0), estado="en_curso", asistencia=False)
    en_curso.fin_at = None
    en_curso.inicio_at = ahora()  # si empezara hace más de 6 h se cerraría sola como parcial (depende de la hora)
    db.commit()
    sesion(db, mi_id(client, beto), d(1))
    assert [s["fecha"] for s in client.get("/api/progreso/historial", headers=ana).json()["sesiones"]] == [d(2).isoformat()]
    assert client.get("/api/progreso/historial", headers=beto).json()["total"] == 1


def test_historial_pagina(client, registrar, db):
    h = registrar()
    uid = mi_id(client, h)
    for atras in range(5):
        sesion(db, uid, d(atras))
    p2 = client.get("/api/progreso/historial", params={"pagina": 2, "por_pagina": 2}, headers=h).json()
    assert p2["total"] == 5 and p2["pagina"] == 2
    assert [s["fecha"] for s in p2["sesiones"]] == [d(2).isoformat(), d(3).isoformat()]


def test_historial_valida_la_paginacion(client, registrar):
    h = registrar()
    for params in ({"pagina": 0}, {"por_pagina": 0}, {"por_pagina": 51}):
        assert client.get("/api/progreso/historial", params=params, headers=h).status_code == 422
