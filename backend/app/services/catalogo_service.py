"""Consultas del catálogo y búsqueda de alternativas (PG-15, PG-16, PG-17)."""
import unicodedata
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ejercicio, EjercicioMaquina, EjercicioMusculo, GrupoMuscular, MaquinaCatalogo
from app.schemas.catalogo import (
    AlternativaOut, ContraindicacionOut, EjercicioFichaOut, EjercicioResumenOut, MaquinaOut, MaquinaResumenOut,
)
from app.services.errores import ErrorNegocio

ORDEN_DIFICULTAD = {"facil": 0, "media": 1, "dificil": 2}


def maquinas_activas(db: Session) -> list[MaquinaCatalogo]:
    # Una máquina desactivada no se ofrece en búsquedas (sigue existiendo para los inventarios que ya la tienen).
    return list(db.scalars(select(MaquinaCatalogo).where(MaquinaCatalogo.activa.is_(True)).order_by(MaquinaCatalogo.nombre)))


def musculos_principales(db: Session) -> dict[int, GrupoMuscular]:
    """Músculo principal de cada máquina = el que más trabajan sus ejercicios (PG-09 lo muestra en cada opción)."""
    conteo: dict[int, Counter] = {}
    grupos: dict[int, GrupoMuscular] = {}
    filas = db.execute(
        select(EjercicioMaquina.maquina_id, GrupoMuscular)
        .join(Ejercicio, Ejercicio.id == EjercicioMaquina.ejercicio_id)
        .join(EjercicioMusculo, (EjercicioMusculo.ejercicio_id == Ejercicio.id) & (EjercicioMusculo.rol == "principal"))
        .join(GrupoMuscular, GrupoMuscular.id == EjercicioMusculo.grupo_id)
        .where(Ejercicio.activo.is_(True))
    )
    for maquina_id, grupo in filas:
        conteo.setdefault(maquina_id, Counter())[grupo.id] += 1
        grupos[grupo.id] = grupo
    # En empate gana el grupo con id menor, para que el resultado sea siempre el mismo.
    return {m: grupos[min(c.items(), key=lambda t: (-t[1], t[0]))[0]] for m, c in conteo.items()}


def _sin_tildes(t: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(ch) != "Mn")


def buscar_maquinas(db: Session, *, q: str | None = None, grupo: str | None = None) -> list[MaquinaCatalogo]:
    """PG-09: búsqueda a mano en el catálogo por nombre (u otro nombre común) o por músculo principal."""
    maquinas = maquinas_activas(db)
    if grupo:
        principales = musculos_principales(db)
        maquinas = [m for m in maquinas if (g := principales.get(m.id)) is not None and g.codigo == grupo]
    if q and q.strip():
        palabras = _sin_tildes(q).split()
        maquinas = [
            m for m in maquinas
            if all(p in _sin_tildes(" ".join([m.nombre, m.codigo.replace("_", " "), *(m.otros_nombres or [])])) for p in palabras)
        ]
    return maquinas


def a_maquina_out(db: Session, m: MaquinaCatalogo, principales: dict[int, GrupoMuscular] | None = None) -> MaquinaOut:
    n = len(db.scalars(select(EjercicioMaquina.id).where(EjercicioMaquina.maquina_id == m.id)).all())
    principal = (principales if principales is not None else musculos_principales(db)).get(m.id)
    return MaquinaOut(
        id=m.id, codigo=m.codigo, nombre=m.nombre, otros_nombres=list(m.otros_nombres or []),
        tipo=m.tipo, fotos=[f.url for f in m.fotos], ejercicios=n,
        musculo_principal=principal.nombre if principal else None,
    )


def _resumen_maquinas(e: Ejercicio) -> list[MaquinaResumenOut]:
    return [MaquinaResumenOut(codigo=x.maquina.codigo, nombre=x.maquina.nombre) for x in e.maquinas]


def a_resumen(e: Ejercicio) -> EjercicioResumenOut:
    principal = e.musculo_principal
    return EjercicioResumenOut(
        id=e.id, codigo=e.codigo, nombre=e.nombre, musculo_principal=principal.codigo if principal else None,
        dificultad=e.dificultad, categoria_equipo=e.categoria_equipo, maquinas=_resumen_maquinas(e),
    )


def a_ficha(e: Ejercicio) -> EjercicioFichaOut:
    base = a_resumen(e).model_dump()
    return EjercicioFichaOut(
        **base,
        musculos_secundarios=[m.grupo.codigo for m in e.musculos if m.rol == "secundario"],
        multiarticular=e.multiarticular, instrucciones=e.instrucciones,
        contraindicaciones=[
            ContraindicacionOut(zona=c.zona.codigo, zona_nombre=c.zona.nombre, nivel=c.nivel) for c in e.contraindicaciones
        ],
        contraindicaciones_revisadas=e.contraindicaciones_revisadas,
    )


def grupos(db: Session) -> list[GrupoMuscular]:
    return list(db.scalars(select(GrupoMuscular).order_by(GrupoMuscular.id)))


def listar_ejercicios(
    db: Session, *, grupo: str | None = None, categoria: str | None = None, maquina: str | None = None
) -> list[Ejercicio]:
    consulta = select(Ejercicio).where(Ejercicio.activo.is_(True)).order_by(Ejercicio.nombre)
    if grupo:
        consulta = consulta.join(EjercicioMusculo).join(GrupoMuscular).where(
            GrupoMuscular.codigo == grupo, EjercicioMusculo.rol == "principal"
        )
    if categoria:
        consulta = consulta.where(Ejercicio.categoria_equipo == categoria)
    if maquina:
        consulta = consulta.join(EjercicioMaquina).join(MaquinaCatalogo, EjercicioMaquina.maquina_id == MaquinaCatalogo.id).where(
            MaquinaCatalogo.codigo == maquina.upper()
        )
    return list(db.scalars(consulta).unique())


def obtener_ejercicio(db: Session, ejercicio_id: int) -> Ejercicio:
    e = db.get(Ejercicio, ejercicio_id)
    if e is None or not e.activo:
        raise ErrorNegocio("Ejercicio no encontrado.", 404)
    return e


def disponible(e: Ejercicio, codigos_maquinas: set[str] | None) -> bool:
    """¿Se puede hacer este ejercicio con lo que hay? Sin equipo: siempre. Con equipo: debe haber una máquina
    activa (y, si se indica, que esté entre las disponibles del gym)."""
    if e.categoria_equipo == "sin_equipo":
        return True
    activas = [x.maquina for x in e.maquinas if x.maquina.activa]
    if codigos_maquinas is None:
        return bool(activas)
    return any(m.codigo in codigos_maquinas for m in activas)


def revisar_lesiones(e: Ejercicio, zonas: dict[str, str]) -> tuple[bool, bool, str | None]:
    """PG-20, regla dura: (permitido, con_precaucion, zona_que_lo_impide).
    - "evitar" en una zona con lesión activa o en reintroducción → nunca.
    - "precaución" → solo si la lesión de esa zona está en reintroducción (y sale marcado); si está activa, nunca."""
    precaucion = False
    for c in e.contraindicaciones:
        estado = zonas.get(c.zona.codigo)
        if estado is None:
            continue
        if c.nivel == "evitar" or estado == "activa":
            return False, False, c.zona.codigo
        precaucion = True
    return True, precaucion, None


def alternativas(
    db: Session, ejercicio: Ejercicio, *, zonas: dict[str, str] | None = None,
    maquinas_disponibles: set[str] | None = None, limite: int = 12,
) -> list[AlternativaOut]:
    """PG-17. Orden de búsqueda: 1) otra máquina del mismo músculo principal, 2) peso libre, 3) sin equipo.
    Todo reemplazo respeta las lesiones con la misma regla del plan (revisar_lesiones): lo que no está permitido
    nunca se propone y lo que pide precaución se propone marcado."""
    zonas = zonas or {}
    principal = ejercicio.musculo_principal
    if principal is None:
        return []

    candidatos = listar_ejercicios(db, grupo=principal.codigo)
    resultado: list[AlternativaOut] = []
    for nivel, categoria in ((1, "maquina"), (2, "peso_libre"), (3, "sin_equipo")):
        grupo_nivel = []
        for c in candidatos:
            if c.id == ejercicio.id or c.categoria_equipo != categoria or not disponible(c, maquinas_disponibles):
                continue
            permitido, precaucion, _ = revisar_lesiones(c, zonas)
            if not permitido:
                continue
            grupo_nivel.append((c, precaucion))
        # Dentro de cada nivel, primero los de dificultad más parecida al ejercicio original.
        grupo_nivel.sort(key=lambda t: (abs(ORDEN_DIFICULTAD[t[0].dificultad] - ORDEN_DIFICULTAD[ejercicio.dificultad]), t[0].nombre))
        for c, precaucion in grupo_nivel:
            resultado.append(AlternativaOut(**a_resumen(c).model_dump(), nivel_busqueda=nivel, precaucion=precaucion))
    return resultado[:limite]
