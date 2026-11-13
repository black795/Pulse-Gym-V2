"""Progreso (Sprint 5): constancia y racha (PG-38), historial de sesiones (PG-46), historial de máquinas y pesos con
récords (PG-40) y alertas de retorno (PG-42) y estancamiento (PG-43).

Solo lectura: usa lo que deja la sesión en vivo (`cuenta_asistencia`, `fecha`, series) sin tablas nuevas.
Las reglas de progresión están en progresion.py (puras) y el peso sugerido en pesos_service.py.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Ejercicio, SesionEntreno, Usuario
from app.schemas.plan import PesoSugeridoOut
from app.schemas.progreso import (
    AlertaOut, AlertasOut, ConstanciaOut, EjercicioDetalleOut, EjercicioUsadoOut, EjerciciosUsadosOut, HistorialOut,
    MarcaOut, SerieHistorialOut, SesionHistorialOut, VezOut,
)
from app.services import catalogo_service, lesion_service, pesos_service, plan_service, progresion, sesion_service
from app.services.errores import ErrorNegocio

MAX_PUNTOS_GRAFICO = 60
MAX_ALERTAS_ESTANCAMIENTO = 3


def calcular_rachas(fechas: set[date], hoy: date) -> tuple[int, int]:
    """(racha actual, mejor racha) en días consecutivos con sesión completa.

    La racha actual sigue viva si el último día entrenado es hoy o ayer: todavía puedes entrenar hoy sin perderla.
    Regla de negocio PROPUESTA (la guía solo dice «5 días»): días calendario consecutivos, sin días de descanso.
    """
    if not fechas:
        return 0, 0
    mejor = largo = 0
    previo: date | None = None
    for f in sorted(fechas):
        largo = largo + 1 if previo is not None and f - previo == timedelta(days=1) else 1
        mejor = max(mejor, largo)
        previo = f
    inicio = hoy if hoy in fechas else hoy - timedelta(days=1)
    actual = 0
    while inicio - timedelta(days=actual) in fechas:
        actual += 1
    return actual, mejor


def constancia(db: Session, usuario: Usuario, hoy: date) -> ConstanciaOut:
    fechas = set(db.scalars(select(SesionEntreno.fecha).where(
        SesionEntreno.usuario_id == usuario.id, SesionEntreno.cuenta_asistencia.is_(True),
    ).distinct()))
    # Se cuentan sesiones, no días: dos sesiones completas el mismo día suman 2.
    lunes = hoy - timedelta(days=hoy.weekday())
    domingo = lunes + timedelta(days=6)
    base = select(func.count()).select_from(SesionEntreno).where(
        SesionEntreno.usuario_id == usuario.id, SesionEntreno.cuenta_asistencia.is_(True))
    semana = db.scalar(base.where(SesionEntreno.fecha.between(lunes, domingo))) or 0
    primero = hoy.replace(day=1)
    siguiente = (primero + timedelta(days=32)).replace(day=1)
    mes = db.scalar(base.where(SesionEntreno.fecha >= primero, SesionEntreno.fecha < siguiente)) or 0
    actual, mejor = calcular_rachas(fechas, hoy)
    return ConstanciaOut(
        racha_actual=actual, mejor_racha=mejor, entreno_hoy=hoy in fechas, sesiones_semana=semana,
        sesiones_mes=mes, ultima_sesion=max((f for f in fechas if f <= hoy), default=None),
    )


def historial(db: Session, usuario: Usuario, pagina: int, por_pagina: int) -> HistorialOut:
    """Sesiones terminadas (completas y parciales), de la más reciente a la más antigua. Solo las del usuario."""
    sesion_service.en_curso(db, usuario)  # cierra las olvidadas para que aparezcan como parciales
    filtro = (SesionEntreno.usuario_id == usuario.id, SesionEntreno.estado != "en_curso")
    total = db.scalar(select(func.count()).select_from(SesionEntreno).where(*filtro)) or 0
    filas = db.scalars(select(SesionEntreno).where(*filtro).order_by(SesionEntreno.fecha.desc(), SesionEntreno.id.desc())
                       .offset((pagina - 1) * por_pagina).limit(por_pagina)).all()
    sesiones = []
    for s in filas:
        hechas, planeadas, volumen = sesion_service._totales(s)
        duracion = int((s.fin_at - s.inicio_at).total_seconds()) if s.fin_at else 0
        sesiones.append(SesionHistorialOut(
            id=s.id, fecha=s.fecha, dia=s.dia_semana, enfoque=s.enfoque, gym_nombre=s.gym_nombre,  # type: ignore[arg-type]
            estado=s.estado, cuenta_asistencia=s.cuenta_asistencia, duracion_seg=duracion, series_hechas=hechas,
            series_planeadas=planeadas, volumen_kg=volumen,
            records=sum(1 for e in s.ejercicios for x in e.series_hechas if x.es_record),
        ))
    return HistorialOut(total=total, pagina=pagina, por_pagina=por_pagina, sesiones=sesiones)


# ---------------- Historial de máquinas y pesos (solo lo que ya hiciste) ----------------
def _campos(e: Ejercicio, veces: list[pesos_service.Vez], grupos: dict[str, str],
            sugerencia: PesoSugeridoOut | None) -> dict:
    ultima, primera = veces[0], veces[-1]
    mejor = max((s.peso_kg, s.repeticiones) for v in veces for s in v.series)
    return dict(
        ejercicio=plan_service.ejercicio_breve(e, grupos), veces=len(veces), primera_fecha=primera.fecha,
        ultima_fecha=ultima.fecha, ultima=[MarcaOut(peso_kg=s.peso_kg, repeticiones=s.repeticiones) for s in ultima.series],
        peso_inicial_kg=max(s.peso_kg for s in primera.series), peso_actual_kg=max(s.peso_kg for s in ultima.series),
        mejor=MarcaOut(peso_kg=mejor[0], repeticiones=mejor[1]), sugerencia=sugerencia,
    )


def _sugerencias(db: Session, usuario: Usuario, ejercicios: dict[int, Ejercicio], veces: dict[int, list[pesos_service.Vez]],
                 hoy: date) -> dict[int, PesoSugeridoOut]:
    """El peso para la próxima vez, con el rango de repeticiones de la última vez y tus lesiones de hoy."""
    zonas = lesion_service.zonas_por_estado(usuario)
    pedidos = [pesos_service.Pedido(e, veces[eid][0].reps_min, veces[eid][0].reps_max,
                                    catalogo_service.revisar_lesiones(e, zonas)[1]) for eid, e in ejercicios.items()]
    return pesos_service.sugerir(db, usuario, pedidos, hoy, veces)


def ejercicios_usados(db: Session, usuario: Usuario, hoy: date) -> EjerciciosUsadosOut:
    """Las máquinas y ejercicios que ya hiciste (el más reciente primero), con tu último peso, récord y el peso
    sugerido para la próxima vez. Los que nunca hiciste no aparecen."""
    sesion_service.en_curso(db, usuario)  # cierra las olvidadas para que sus series cuenten
    veces = pesos_service.historial(db, usuario.id)
    if not veces:
        return EjerciciosUsadosOut(ejercicios=[])
    ejercicios = {e.id: e for e in db.scalars(select(Ejercicio).where(Ejercicio.id.in_(veces)))}
    sugerencias = _sugerencias(db, usuario, ejercicios, veces, hoy)
    grupos = plan_service.nombres_grupos(db)
    orden = sorted(veces, key=lambda eid: (veces[eid][0].fecha, veces[eid][0].sesion_id), reverse=True)
    return EjerciciosUsadosOut(ejercicios=[
        EjercicioUsadoOut(**_campos(ejercicios[eid], veces[eid], grupos, sugerencias.get(eid))) for eid in orden
    ])


def _alerta_estancamiento(nombre: str, ejercicio_id: int, peso: float, sesiones: int, dias: int) -> AlertaOut:
    semanas = max(2, round(dias / 7))
    return AlertaOut(
        tipo="estancamiento", ejercicio_id=ejercicio_id, titulo=f"{nombre}: {semanas} semanas con {progresion.kg(peso)}",
        texto=f"Llevas {sesiones} sesiones sin subir el peso ni las repeticiones. Prueba sumar 1 o 2 repeticiones por "
              "serie antes de subir el peso; si sigues igual, cambia a un ejercicio parecido por unas semanas.",
    )


def ejercicio_detalle(db: Session, usuario: Usuario, ejercicio_id: int, hoy: date) -> EjercicioDetalleOut:
    """Evolución de un ejercicio que ya hiciste: cada sesión con sus series, récords y si estás estancado."""
    sesion_service.en_curso(db, usuario)
    veces = pesos_service.historial(db, usuario.id, {ejercicio_id}).get(ejercicio_id)
    if not veces:  # nunca lo hiciste (o es de otra persona): no hay historial que mostrar
        raise ErrorNegocio("Todavía no tienes historial en este ejercicio.", 404)
    e = db.get(Ejercicio, ejercicio_id)
    sugerencia = _sugerencias(db, usuario, {e.id: e}, {e.id: veces}, hoy).get(e.id)
    historial = []
    for v in reversed(veces[:MAX_PUNTOS_GRAFICO]):
        top = max(s.peso_kg for s in v.series)
        historial.append(VezOut(
            sesion_id=v.sesion_id, fecha=v.fecha, gym_nombre=v.gym_nombre, peso_max_kg=top,
            reps_con_peso_max=max(s.repeticiones for s in v.series if s.peso_kg == top),
            volumen_kg=round(sum(s.peso_kg * s.repeticiones for s in v.series), 1), record=any(s.es_record for s in v.series),
            series=[SerieHistorialOut(numero=s.numero, peso_kg=s.peso_kg, repeticiones=s.repeticiones, es_record=s.es_record)
                    for s in v.series],
        ))
    estancado = progresion.estancamiento([v.pasada() for v in veces], hoy)
    return EjercicioDetalleOut(
        **_campos(e, veces, plan_service.nombres_grupos(db), sugerencia), historial=historial,
        estancamiento=_alerta_estancamiento(e.nombre, e.id, *estancado) if estancado else None,
    )


def alertas(db: Session, usuario: Usuario, hoy: date) -> AlertasOut:
    """PG-42: volviste después de 2 semanas o más (los pesos de hoy bajan 10 %). PG-43: ejercicios estancados."""
    sesion_service.en_curso(db, usuario)
    lista: list[AlertaOut] = []
    anterior = db.scalar(select(func.max(SesionEntreno.fecha)).where(
        SesionEntreno.usuario_id == usuario.id, SesionEntreno.estado != "en_curso", SesionEntreno.fecha < hoy))
    if anterior is not None and (hoy - anterior).days >= progresion.DIAS_RETORNO:
        semanas = (hoy - anterior).days // 7
        lista.append(AlertaOut(
            tipo="retorno", titulo=f"Volviste después de {semanas} semanas",
            texto="Hoy bajamos tus pesos un 10 % para cuidar tus articulaciones. En pocas sesiones vuelves a tu nivel.",
        ))
    veces = pesos_service.historial(db, usuario.id)
    estancados = []
    for eid, lista_veces in veces.items():
        r = progresion.estancamiento([v.pasada() for v in lista_veces], hoy)
        if r is not None:
            estancados.append((eid, *r))
    estancados.sort(key=lambda x: x[3], reverse=True)  # los que llevan más días, primero
    estancados = estancados[:MAX_ALERTAS_ESTANCAMIENTO]
    if estancados:
        nombres = dict(db.execute(select(Ejercicio.id, Ejercicio.nombre)
                                  .where(Ejercicio.id.in_([x[0] for x in estancados]))).all())
        lista += [_alerta_estancamiento(nombres[eid], eid, peso, n, dias) for eid, peso, n, dias in estancados]
    return AlertasOut(alertas=lista)
