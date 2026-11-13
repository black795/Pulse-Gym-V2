"""Historial de pesos por ejercicio y peso sugerido (Sprint 5: PG-41, PG-42).

Lee lo que dejó la sesión en vivo (serie_registrada) y se lo pasa a las reglas puras de progresion.py. Lo usan el
plan, "Hoy", la sesión en vivo y el panel de progreso. Solo lectura: no escribe en la base de datos.

Solo cuentan las sesiones terminadas (completas, parciales o registradas a mano): la sesión en curso no se compara
consigo misma.
"""
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ejercicio, Rutina, SerieRegistrada, SesionEjercicio, SesionEntreno, Usuario
from app.schemas.plan import PesoSugeridoOut
from app.services import progresion


@dataclass
class SerieVez:
    numero: int
    peso_kg: float
    repeticiones: int
    es_record: bool


@dataclass
class Vez:
    """Una sesión en la que hiciste el ejercicio."""
    sesion_id: int
    fecha: date
    gym_nombre: str | None
    series_plan: int
    reps_min: int
    reps_max: int
    series: list[SerieVez] = field(default_factory=list)

    def pasada(self) -> progresion.SesionPasada:
        return progresion.SesionPasada(
            fecha=self.fecha, series=[(s.peso_kg, s.repeticiones) for s in self.series],
            series_plan=self.series_plan, reps_min=self.reps_min, reps_max=self.reps_max,
        )


def historial(db: Session, usuario_id: int, ejercicio_ids: Iterable[int] | None = None) -> dict[int, list[Vez]]:
    """ejercicio_id → veces que lo hiciste (de la más reciente a la más antigua). Solo ejercicios con alguna serie.
    Una sola consulta por columnas (sin cargar relaciones), para no hacer una consulta por ejercicio."""
    q = (
        select(SesionEntreno.id, SesionEntreno.fecha, SesionEntreno.gym_nombre, SesionEjercicio.ejercicio_id,
               SesionEjercicio.series, SesionEjercicio.reps_min, SesionEjercicio.reps_max,
               SerieRegistrada.numero_serie, SerieRegistrada.peso_kg, SerieRegistrada.repeticiones, SerieRegistrada.es_record)
        .join(SesionEjercicio, SesionEjercicio.sesion_id == SesionEntreno.id)
        .join(SerieRegistrada, SerieRegistrada.sesion_ejercicio_id == SesionEjercicio.id)
        .where(SesionEntreno.usuario_id == usuario_id, SesionEntreno.estado != "en_curso")
        .order_by(SesionEntreno.fecha.desc(), SesionEntreno.inicio_at.desc(), SesionEntreno.id.desc(),
                  SerieRegistrada.numero_serie)
    )
    if ejercicio_ids is not None:
        ids = set(ejercicio_ids)
        if not ids:
            return {}
        q = q.where(SesionEjercicio.ejercicio_id.in_(ids))
    resultado: dict[int, list[Vez]] = {}
    for (sid, fecha, gym, eid, series, rmin, rmax, numero, peso, reps, record) in db.execute(q):
        veces = resultado.setdefault(eid, [])
        if not veces or veces[-1].sesion_id != sid:
            veces.append(Vez(sid, fecha, gym, series, rmin, rmax))
        vez = veces[-1]
        vez.series_plan = max(vez.series_plan, series)  # por si el ejercicio quedó dos veces (reemplazo en vivo)
        vez.series.append(SerieVez(numero, peso, reps, record))
    return resultado


def perfil_fisico(usuario: Usuario) -> progresion.PerfilFisico:
    peso = next((m.peso_kg for m in usuario.mediciones if m.peso_kg is not None), None)
    return progresion.PerfilFisico(
        nivel=usuario.objetivo.nivel if usuario.objetivo else None, sexo=usuario.sexo, edad=usuario.edad, peso_kg=peso,
    )


def datos_ejercicio(e: Ejercicio, precaucion: bool = False) -> progresion.EjercicioDatos:
    principal = e.musculo_principal
    return progresion.EjercicioDatos(e.categoria_equipo, e.multiarticular, principal.codigo if principal else None, precaucion)


def pesos_base(db: Session, usuario_id: int) -> dict[str, dict]:
    """Los pesos iniciales que estimó la IA al armar el plan activo (ejercicio_id → {"kg", "origen"})."""
    rutina = db.scalar(select(Rutina).where(Rutina.usuario_id == usuario_id, Rutina.estado == "activa")
                       .order_by(Rutina.version.desc()).limit(1))
    return dict((rutina.parametros or {}).get("pesos_base", {})) if rutina else {}


@dataclass
class Pedido:
    ejercicio: Ejercicio
    reps_min: int
    reps_max: int
    precaucion: bool = False


def a_out(s: progresion.Sugerencia, origen: str) -> PesoSugeridoOut:
    return PesoSugeridoOut(peso_kg=s.peso_kg, reps=s.reps, tipo=s.tipo, origen=origen, texto=s.texto)  # type: ignore[arg-type]


def sugerir(db: Session, usuario: Usuario, pedidos: list[Pedido], hoy: date,
            veces: dict[int, list[Vez]] | None = None) -> dict[int, PesoSugeridoOut]:
    """ejercicio_id → peso sugerido para hoy. Con historial: progresión (PG-41/42). Sin historial: el peso inicial
    que estimó la IA al armar el plan o, si no hay, el de reglas. Los ejercicios sin peso que nunca hiciste no llevan
    sugerencia (se hacen con tu cuerpo)."""
    if not pedidos:
        return {}
    if veces is None:
        veces = historial(db, usuario.id, {p.ejercicio.id for p in pedidos})
    base = pesos_base(db, usuario.id)
    perfil = perfil_fisico(usuario)
    resultado: dict[int, PesoSugeridoOut] = {}
    for p in pedidos:
        e = p.ejercicio
        if e.id in resultado:
            continue
        hist = veces.get(e.id)
        if hist:
            s = progresion.sugerir([v.pasada() for v in hist], hoy, p.reps_min, p.reps_max, e.multiarticular, p.precaucion)
            if s is not None:
                resultado[e.id] = a_out(s, "historial")
            continue
        if e.categoria_equipo == "sin_equipo":
            continue
        guardado = base.get(str(e.id))
        if guardado and isinstance(guardado.get("kg"), (int, float)):
            peso, origen = progresion.redondear(guardado["kg"]), guardado.get("origen", "ia")
            if p.precaucion and not guardado.get("precaucion"):
                peso = progresion.redondear(peso * progresion.FACTOR_PRECAUCION)  # la lesión apareció después del plan
        else:
            peso, origen = progresion.peso_inicial_reglas(datos_ejercicio(e, p.precaucion), perfil), "reglas"
        resultado[e.id] = a_out(progresion.sugerencia_inicial(peso, p.reps_max, origen), origen)
    return resultado
