"""Caracterización de la normalización usada por catálogo y reglas de planes."""
from types import SimpleNamespace

import pytest

from app.services import catalogo_service, plan_reglas
from tests.test_plan import ctx_ficticio


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("ÁÉÍÓÚ Ñ Ü", "aeiou n u"),
        ("MiXeD minúsculas", "mixed minusculas"),
        ("  PróNACIÓN\t", "  pronacion\t"),
        ("Cafe\u0301", "cafe"),
        ("\u0301", ""),
        ("", ""),
        ("   ", "   "),
        ("Straße Ø ①", "straße ø ①"),
        ("İSTANBUL", "istanbul"),
        ("東京 🏋️", "東京 🏋"),
    ],
)
def test_las_dos_normalizaciones_conservan_el_contrato(texto, esperado):
    assert catalogo_service._sin_tildes(texto) == esperado
    assert plan_reglas.sin_tildes(texto) == esperado


@pytest.mark.parametrize("normalizar", [catalogo_service._sin_tildes, plan_reglas.sin_tildes])
def test_la_normalizacion_no_acepta_none(normalizar):
    with pytest.raises(AttributeError):
        normalizar(None)


@pytest.mark.parametrize(
    ("consulta", "esperados"),
    [
        ("  EXTENSIÓN  CUADRICEPS ", ["EXT_CUADRICEPS"]),
        ("cua\u0301driceps", ["EXT_CUADRICEPS"]),
        ("LEG PRESS", ["PRENSA_45"]),
        ("PRENSA 45", ["PRENSA_45"]),
        ("東京", ["TOKIO"]),
        ("   ", ["EXT_CUADRICEPS", "PRENSA_45", "TOKIO"]),
        ("inexistente", []),
    ],
)
def test_busqueda_de_maquinas_normaliza_nombre_codigo_y_alias(monkeypatch, consulta, esperados):
    maquinas = [
        SimpleNamespace(nombre="Extensión de cuádriceps", codigo="EXT_CUADRICEPS", otros_nombres=[]),
        SimpleNamespace(nombre="Prensa", codigo="PRENSA_45", otros_nombres=["Leg press"]),
        SimpleNamespace(nombre="東京", codigo="TOKIO", otros_nombres=[]),
    ]
    monkeypatch.setattr(catalogo_service, "maquinas_activas", lambda _db: maquinas)

    assert [m.codigo for m in catalogo_service.buscar_maquinas(None, q=consulta)] == esperados


@pytest.mark.parametrize("explicacion", ["Cuidamos tu RODILLA.", "Cuidamos tu rodi\u0301lla."])
def test_validar_plan_reconoce_la_zona_sin_duplicar_la_explicacion(explicacion):
    ctx = ctx_ficticio(["lunes"], zonas={"rodilla": "activa"}, nombres_zonas={"rodilla": "Rodílla"})
    plan = plan_reglas.armar_con_reglas(ctx)
    plan.explicacion = explicacion

    revision = plan_reglas.validar(plan, ctx)

    assert revision.ok
    assert revision.plan.explicacion == explicacion
    assert "se agregó cómo se tuvo en cuenta la lesión" not in revision.correcciones


def test_validar_plan_agrega_la_zona_cuando_no_esta_en_la_explicacion():
    ctx = ctx_ficticio(["lunes"], zonas={"rodilla": "activa"}, nombres_zonas={"rodilla": "Rodílla"})
    plan = plan_reglas.armar_con_reglas(ctx)
    plan.explicacion = "Plan de entrenamiento."

    revision = plan_reglas.validar(plan, ctx)

    assert revision.ok
    assert revision.plan.explicacion == "Plan de entrenamiento. Cuidamos tu rodílla: quitamos los ejercicios que la pueden empeorar."
    assert "se agregó cómo se tuvo en cuenta la lesión" in revision.correcciones
