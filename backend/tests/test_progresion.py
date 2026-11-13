"""Sprint 5: reglas puras de progresión de pesos (PG-41 sobrecarga, PG-42 retorno, PG-43 estancamiento) y el peso
inicial (reglas y margen para el que propone la IA)."""
from datetime import date, timedelta

import pytest

from app.services import progresion as p

HOY = date(2026, 11, 12)


def vez(dias_atras, series, plan=3, rmin=8, rmax=10):
    return p.SesionPasada(HOY - timedelta(days=dias_atras), series, plan, rmin, rmax)


# ---------------- PG-41: doble progresión ----------------
def test_sin_historial_no_hay_sugerencia():
    assert p.sugerir([], HOY, 8, 10, True) is None


def test_si_completaste_todas_las_series_al_tope_sube():
    s = p.sugerir([vez(3, [(40, 10), (40, 10), (40, 10)])], HOY, 8, 10, True)
    assert (s.tipo, s.peso_kg, s.reps) == ("subir", 42.5, 8)
    assert "42,5 kg" in s.texto


def test_una_articulacion_sube_menos():
    assert p.sugerir([vez(3, [(20, 12)] * 3, rmax=12)], HOY, 10, 12, False).peso_kg == 21


def test_con_pesos_chicos_el_escalon_no_pasa_del_10_por_ciento():
    assert p.sugerir([vez(3, [(5, 12)] * 3, rmax=12)], HOY, 10, 12, False).peso_kg == 5.5


def test_si_falto_una_serie_mantiene_e_intenta_una_repeticion_mas():
    s = p.sugerir([vez(3, [(40, 10), (40, 10), (40, 9)])], HOY, 8, 10, True)
    assert (s.tipo, s.peso_kg, s.reps) == ("mantener", 40, 10)


def test_solo_cuentan_las_series_con_el_peso_mas_alto():
    # Dos series al tope, pero con menos peso: no alcanza para subir.
    s = p.sugerir([vez(3, [(30, 10), (30, 10), (40, 10)])], HOY, 8, 10, True)
    assert s.tipo == "mantener" and s.peso_kg == 40


def test_si_no_llegaste_al_minimo_baja():
    s = p.sugerir([vez(3, [(50, 6), (50, 5), (50, 5)])], HOY, 8, 10, True)
    assert (s.tipo, s.peso_kg) == ("bajar", 47.5)


def test_con_precaucion_nunca_sube():
    s = p.sugerir([vez(3, [(40, 10)] * 3)], HOY, 8, 10, True, precaucion=True)
    assert (s.tipo, s.peso_kg) == ("mantener", 40)


def test_sin_peso_sugiere_mas_repeticiones():
    s = p.sugerir([vez(3, [(0, 12), (0, 15)])], HOY, 8, 15, False)
    assert (s.peso_kg, s.reps, s.tipo) == (0, 16, "mantener")  # una más que tu mejor serie


def test_usa_la_vez_mas_reciente():
    s = p.sugerir([vez(2, [(45, 9)] * 3), vez(9, [(40, 10)] * 3)], HOY, 8, 10, True)
    assert s.peso_kg == 45 and s.tipo == "mantener"


# ---------------- PG-42: retorno tras una ausencia ----------------
def test_despues_de_dos_semanas_baja_10_por_ciento():
    s = p.sugerir([vez(20, [(50, 10)] * 3)], HOY, 8, 10, True)
    assert (s.tipo, s.peso_kg) == ("retorno", 45)
    assert "2 semanas" in s.texto


def test_trece_dias_todavia_no_es_retorno():
    assert p.sugerir([vez(13, [(50, 10)] * 3)], HOY, 8, 10, True).tipo == "subir"


# ---------------- PG-43: estancamiento ----------------
def test_tres_sesiones_en_dos_semanas_con_el_mismo_peso_es_estancamiento():
    h = [vez(1, [(40, 8)] * 3), vez(8, [(40, 8)] * 3), vez(15, [(40, 8)] * 3)]
    assert p.estancamiento(h, HOY) == (40, 3, 14)


def test_si_mejoraste_las_repeticiones_no_es_estancamiento():
    h = [vez(1, [(40, 9)] * 3), vez(8, [(40, 8)] * 3), vez(15, [(40, 8)] * 3)]
    assert p.estancamiento(h, HOY) is None


def test_si_subiste_de_peso_no_es_estancamiento():
    h = [vez(1, [(42.5, 8)] * 3), vez(8, [(40, 8)] * 3), vez(15, [(40, 8)] * 3)]
    assert p.estancamiento(h, HOY) is None


def test_pocas_sesiones_o_poco_tiempo_no_es_estancamiento():
    assert p.estancamiento([vez(1, [(40, 8)]), vez(8, [(40, 8)])], HOY) is None
    assert p.estancamiento([vez(1, [(40, 8)]), vez(3, [(40, 8)]), vez(5, [(40, 8)])], HOY) is None


def test_tras_una_ausencia_no_se_habla_de_estancamiento():
    h = [vez(20, [(40, 8)]), vez(27, [(40, 8)]), vez(34, [(40, 8)])]
    assert p.estancamiento(h, HOY) is None


# ---------------- Peso inicial y margen de la IA ----------------
PRENSA = p.EjercicioDatos("maquina", True, "cuadriceps")
CURL = p.EjercicioDatos("peso_libre", False, "biceps")


def test_peso_inicial_segun_el_perfil():
    hombre = p.PerfilFisico(nivel="principiante", sexo="masculino", peso_kg=80)
    assert p.peso_inicial_reglas(PRENSA, hombre) == 48  # 80 × 0,6
    mujer = p.PerfilFisico(nivel="principiante", sexo="femenino", peso_kg=80)
    assert p.peso_inicial_reglas(PRENSA, mujer) < p.peso_inicial_reglas(PRENSA, hombre)
    avanzado = p.PerfilFisico(nivel="avanzado", sexo="masculino", peso_kg=80)
    assert p.peso_inicial_reglas(PRENSA, avanzado) > p.peso_inicial_reglas(PRENSA, hombre)


def test_peso_inicial_sin_equipo_es_cero_y_con_precaucion_menor():
    perfil = p.PerfilFisico(nivel="intermedio", sexo="masculino", peso_kg=70)
    assert p.peso_inicial_reglas(p.EjercicioDatos("sin_equipo", True, "pecho"), perfil) == 0
    cuidado = p.EjercicioDatos("maquina", True, "cuadriceps", precaucion=True)
    assert p.peso_inicial_reglas(cuidado, perfil) < p.peso_inicial_reglas(PRENSA, perfil)


def test_peso_inicial_sin_datos_usa_valores_prudentes_y_un_minimo():
    assert p.peso_inicial_reglas(CURL, p.PerfilFisico()) >= 2
    assert p.peso_inicial_reglas(CURL, p.PerfilFisico()) % 0.5 == 0


@pytest.mark.parametrize("ia, esperado", [(45, 45), (500, 60), (1, 20), (-5, 20), (None, None), (float("nan"), None)])
def test_el_peso_de_la_ia_se_acota_a_un_margen_de_las_reglas(ia, esperado):
    assert p.validar_peso_ia(ia, 40) == esperado


def test_sin_equipo_la_ia_no_puede_poner_peso():
    assert p.validar_peso_ia(30, 0) == 0


def test_redondeo_de_medio_kilo_y_limites():
    assert p.redondear(42.3) == 42.5 and p.redondear(-3) == 0 and p.redondear(900) == 500
