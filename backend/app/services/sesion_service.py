"""Sesión en vivo (Sprint 4): iniciar y congelar (PG-30), cronómetro (PG-34), registrar series (PG-35), récords
(PG-40), máquina ocupada (PG-29), "me molesta" (PG-22) y finalizar con calificación (PG-37).

No usa IA: todo son reglas (rápido, gratis y funciona aunque la IA esté caída). El descanso con sonido (PG-36) vive
en la app; el backend solo le da el descanso de cada ejercicio.
"""
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import Ejercicio, Gym, Rutina, RutinaDia, SerieRegistrada, SesionEjercicio, SesionEntreno, Usuario, ZonaLesion
from app.schemas.lesion import LesionIn
from app.schemas.plan import SesionHoyOut
from app.schemas.sesion import (
    IniciarSesionIn, MejorMarcaOut, OpcionesReemplazoOut, RecordOut, ReemplazoIn, ResumenOut, SerieAnteriorOut, SerieIn,
    SerieOut, SesionEjercicioOut, SesionOut, SesionPasadaIn,
)
from app.services import adaptacion_service, catalogo_service, gym_service, lesion_service, pesos_service, plan_service
from app.services import progresion
from app.services import plan_reglas as reglas
from app.services.errores import ErrorNegocio

TEXTO_MOTIVO = {"maquina_ocupada": "La máquina estaba ocupada", "molestia_dolor": "Te molestaba"}
# PG-39 (Sprint 5): plazos PROPUESTOS para registrar a mano lo que no se anotó.
HORAS_PARA_COMPLETAR = 48  # "olvidé marcar series" en una sesión parcial
DIAS_ATRAS_PASADA = 7  # registrar un entrenamiento pasado


# ---------------- Consultas ----------------
def _cerrar_olvidadas(db: Session, usuario: Usuario) -> None:
    """Una sesión abierta hace más de N horas se cierra sola con lo que se registró (no queda colgada para siempre)."""
    limite = ahora() - timedelta(hours=get_settings().sesion_horas_max)
    viejas = db.scalars(select(SesionEntreno).where(
        SesionEntreno.usuario_id == usuario.id, SesionEntreno.estado == "en_curso", SesionEntreno.inicio_at < limite,
    )).all()
    for s in viejas:
        ultima = max((x.completada_at for e in s.ejercicios for x in e.series_hechas), default=s.inicio_at)
        _calificar(s, ultima)
        s.cerrada_auto = True
    if viejas:
        db.commit()


def en_curso(db: Session, usuario: Usuario) -> SesionEntreno | None:
    _cerrar_olvidadas(db, usuario)
    return db.scalar(select(SesionEntreno).where(
        SesionEntreno.usuario_id == usuario.id, SesionEntreno.estado == "en_curso",
    ).order_by(SesionEntreno.id.desc()).limit(1))


def obtener(db: Session, usuario: Usuario, sesion_id: int) -> SesionEntreno:
    s = db.get(SesionEntreno, sesion_id)
    if s is None or s.usuario_id != usuario.id:  # la sesión de otra persona "no existe" para ti
        raise ErrorNegocio("Sesión no encontrada.", 404)
    return s


def _en_curso_o_error(db: Session, usuario: Usuario, sesion_id: int) -> SesionEntreno:
    s = obtener(db, usuario, sesion_id)
    _cerrar_olvidadas(db, usuario)
    if s.estado != "en_curso":
        raise ErrorNegocio("Esta sesión ya terminó.", 409, "sesion_terminada")
    return s


def _ejercicio_de(s: SesionEntreno, se_id: int) -> SesionEjercicio:
    se = next((e for e in s.ejercicios if e.id == se_id), None)
    if se is None:
        raise ErrorNegocio("Ese ejercicio no está en esta sesión.", 404)
    return se


# ---------------- PG-30: iniciar y congelar ----------------
def _gym_maquina_id(gym: Gym | None, e: Ejercicio) -> int | None:
    """La máquina del inventario con que se hace (si el ejercicio usa una y está disponible en el gym)."""
    if gym is None:
        return None
    codigos = {x.maquina.codigo for x in e.maquinas}
    return next((gm.id for gm in gym.maquinas if gm.estado == "disponible" and gm.maquina and gm.maquina.codigo in codigos), None)


def _sesion_del_dia(db: Session, usuario: Usuario, gym_id: int | None, dia: str | None, fecha: date) -> SesionHoyOut:
    """El día del plan adaptado al gym (lo mismo que muestra /api/hoy), o un error claro si no se puede entrenar."""
    hoy = adaptacion_service.hoy(db, usuario, gym_id=gym_id, dia=dia, fecha=fecha)
    if not hoy.plan_existe:
        raise ErrorNegocio("Primero arma tu plan semanal.", 400, "sin_plan")
    if hoy.requiere_elegir_gym:
        raise ErrorNegocio("Elige en qué gym estás.", 400, "elegir_gym")
    sesion_hoy = hoy.sesion
    if sesion_hoy is None:
        raise ErrorNegocio("Hoy no toca entrenar según tu plan. Puedes adelantar el siguiente día.", 400, "dia_libre")
    if not sesion_hoy.ejercicios:
        raise ErrorNegocio("No hay ejercicios que puedas hacer hoy en este gym.", 400, "sin_ejercicios")
    return sesion_hoy


def iniciar(db: Session, usuario: Usuario, datos: IniciarSesionIn) -> SesionEntreno:
    actual = en_curso(db, usuario)
    if actual is not None:
        raise ErrorNegocio("Ya tienes una rutina en curso. Termínala antes de empezar otra.", 409, "sesion_en_curso")
    fecha = adaptacion_service.fecha_valida(datos.fecha)
    sesion_hoy = _sesion_del_dia(db, usuario, datos.gym_id, datos.dia, fecha)
    s, gym = _congelar(db, usuario, sesion_hoy, fecha, ahora())
    db.add(s)
    if gym is not None:
        gym.ultimo_uso_at = ahora()  # PG-06: el último gym usado
    db.commit()
    db.refresh(s)
    return s


def _congelar(db: Session, usuario: Usuario, sesion_hoy: SesionHoyOut, fecha: date,
              inicio: datetime) -> tuple[SesionEntreno, Gym | None]:
    """Copia los ejercicios del día ya adaptados al gym en una sesión nueva (todavía sin guardar)."""
    gym = db.get(Gym, sesion_hoy.gym_id) if sesion_hoy.gym_id else None
    rutina = plan_service.activa(db, usuario)
    rutina_dia = next((d for d in rutina.dias if d.dia_semana == sesion_hoy.dia), None) if rutina else None
    # Las adaptaciones guardadas antes del Sprint 4 no traen de qué ejercicio del plan salen: se busca por código.
    del_plan = {re.ejercicio.codigo: re.id for re in rutina_dia.ejercicios} if rutina_dia else {}
    s = SesionEntreno(
        usuario_id=usuario.id, gym_id=gym.id if gym else None, gym_nombre=gym.nombre if gym else None,
        rutina_dia_id=rutina_dia.id if rutina_dia else None, dia_semana=sesion_hoy.dia, enfoque=sesion_hoy.enfoque,
        fecha=fecha, inicio_at=inicio, duracion_estimada_seg=sesion_hoy.minutos_estimados * 60, estado="en_curso",
    )
    for x in sesion_hoy.ejercicios:
        e = db.get(Ejercicio, x.ejercicio.id)
        s.ejercicios.append(SesionEjercicio(
            rutina_ejercicio_id=x.rutina_ejercicio_id or del_plan.get((x.original or x.ejercicio).codigo),
            ejercicio_id=e.id, gym_maquina_id=_gym_maquina_id(gym, e),
            reemplaza_id=x.original.id if x.original else None, orden=x.orden, series=x.series, reps_min=x.reps_min,
            reps_max=x.reps_max, descanso_seg=x.descanso_seg, precaucion=x.precaucion,
            motivo=("sin_equipo" if e.categoria_equipo == "sin_equipo" else "adaptado_gym") if x.cambio else "plan_original",
            nota=" ".join(t for t in (x.motivo_cambio, x.por_que_reemplazo) if t) or None,
        ))
    return s, gym


# ---------------- PG-35 y PG-40: series y récords ----------------
def _historial(db: Session, usuario: Usuario, ejercicio_id: int, antes_de: SesionEntreno) -> list[tuple[SesionEntreno, SerieRegistrada]]:
    """Series de este ejercicio en sesiones anteriores a `antes_de` (más recientes primero)."""
    return list(db.execute(
        select(SesionEntreno, SerieRegistrada)
        .join(SesionEjercicio, SesionEjercicio.sesion_id == SesionEntreno.id)
        .join(SerieRegistrada, SerieRegistrada.sesion_ejercicio_id == SesionEjercicio.id)
        .where(SesionEntreno.usuario_id == usuario.id, SesionEjercicio.ejercicio_id == ejercicio_id,
               SesionEntreno.id != antes_de.id, SesionEntreno.inicio_at <= antes_de.inicio_at)
        .order_by(SesionEntreno.inicio_at.desc(), SesionEntreno.id.desc(), SerieRegistrada.numero_serie)
    ).all())


def _mejor(series: list[tuple[float, int]]) -> tuple[float, int] | None:
    """La mejor marca: más peso; a igual peso, más repeticiones (sin peso: más repeticiones)."""
    return max(series, default=None)


def _supera(serie: tuple[float, int], mejor: tuple[float, int] | None) -> bool:
    """PG-40: es récord si supera tu mejor marca. La primera vez que haces un ejercicio no hay con qué comparar."""
    return mejor is not None and serie > mejor


def _recalcular_records(db: Session, usuario: Usuario, s: SesionEntreno, ejercicio_id: int) -> None:
    """Se recalcula todo el ejercicio en esta sesión (editar o borrar una serie puede cambiar las siguientes)."""
    mejor = _mejor([(x.peso_kg, x.repeticiones) for _, x in _historial(db, usuario, ejercicio_id, s)])
    series = sorted(
        (x for e in s.ejercicios if e.ejercicio_id == ejercicio_id for x in e.series_hechas),
        key=lambda x: (x.completada_at, x.id or 0),
    )
    for x in series:
        marca = (x.peso_kg, x.repeticiones)
        x.es_record = _supera(marca, mejor)
        mejor = marca if mejor is None else max(mejor, marca)  # la primera serie de la historia es la marca a superar


def registrar_serie(db: Session, usuario: Usuario, sesion_id: int, se_id: int, numero: int, datos: SerieIn) -> SesionEntreno:
    """Guarda (o corrige) la serie `numero`. Repetir el mismo pedido no duplica nada (sirve con mala señal en el gym)."""
    s = _en_curso_o_error(db, usuario, sesion_id)
    se = _ejercicio_de(s, se_id)
    if se.cerrado:
        raise ErrorNegocio("Este ejercicio se reemplazó: registra las series en el nuevo.", 409, "ejercicio_cerrado")
    if not 1 <= numero <= se.series + 3:  # se permiten hasta 3 series extra
        raise ErrorNegocio(f"La serie debe estar entre 1 y {se.series + 3}.", 400)
    peso = round(datos.peso_kg * 2) / 2  # de medio en medio kilo, como los discos
    serie = next((x for x in se.series_hechas if x.numero_serie == numero), None)
    if serie is None:
        se.series_hechas.append(SerieRegistrada(numero_serie=numero, peso_kg=peso, repeticiones=datos.repeticiones,
                                                completada_at=ahora()))
    else:
        serie.peso_kg, serie.repeticiones = peso, datos.repeticiones
    db.flush()
    _recalcular_records(db, usuario, s, se.ejercicio_id)
    db.commit()
    return s


def borrar_serie(db: Session, usuario: Usuario, sesion_id: int, se_id: int, numero: int) -> SesionEntreno:
    s = _en_curso_o_error(db, usuario, sesion_id)
    se = _ejercicio_de(s, se_id)
    serie = next((x for x in se.series_hechas if x.numero_serie == numero), None)
    if serie is None:
        raise ErrorNegocio("Esa serie no está registrada.", 404)
    se.series_hechas.remove(serie)
    db.flush()
    _recalcular_records(db, usuario, s, se.ejercicio_id)
    db.commit()
    return s


# ---------------- PG-29 y PG-22: reemplazos en vivo ----------------
def _zonas_con_molestia(db: Session, usuario: Usuario, zona: str | None) -> dict[str, str]:
    zonas = lesion_service.zonas_por_estado(usuario)
    if zona is not None:
        if db.scalar(select(ZonaLesion.id).where(ZonaLesion.codigo == zona)) is None:
            raise ErrorNegocio(f"La zona «{zona}» no existe.", 400)
        zonas[zona] = "activa"  # la zona que molesta se trata como lesión activa: nada que la cargue
    return zonas


def _gym(db: Session, s: SesionEntreno) -> Gym | None:
    return db.get(Gym, s.gym_id) if s.gym_id else None


def _codigos_libres(db: Session, s: SesionEntreno, se: SesionEjercicio, motivo: str) -> set[str]:
    """Lo que hay disponible en el gym de la sesión. Si la máquina está ocupada, esa máquina no cuenta."""
    gym = _gym(db, s)
    codigos = gym_service.codigos_disponibles(gym) if gym else set()
    if motivo == "maquina_ocupada":
        codigos -= {x.maquina.codigo for x in se.ejercicio.maquinas}
    return codigos


def _opciones(db: Session, usuario: Usuario, s: SesionEntreno, se: SesionEjercicio, motivo: str, zona: str | None):
    if motivo == "molestia_dolor" and not zona:
        raise ErrorNegocio("Dinos qué zona te molesta.", 400, "falta_zona")
    zonas = _zonas_con_molestia(db, usuario, zona if motivo == "molestia_dolor" else None)
    en_sesion = {e.ejercicio_id for e in s.ejercicios if not e.cerrado}
    return [a for a in catalogo_service.alternativas(db, se.ejercicio, zonas=zonas,
                                                      maquinas_disponibles=_codigos_libres(db, s, se, motivo), limite=30)
            if a.id not in en_sesion][:6]


def opciones_reemplazo(db: Session, usuario: Usuario, sesion_id: int, se_id: int, motivo: str, zona: str | None) -> OpcionesReemplazoOut:
    s = _en_curso_o_error(db, usuario, sesion_id)
    se = _ejercicio_de(s, se_id)
    if se.cerrado:
        raise ErrorNegocio("Este ejercicio ya se reemplazó.", 409, "ejercicio_cerrado")
    opciones = _opciones(db, usuario, s, se, motivo, zona)
    aviso = None
    if not opciones:
        aviso = ("No encontramos otro ejercicio seguro para ese músculo en este gym. Puedes saltarlo hoy."
                 if motivo == "molestia_dolor" else "No hay otra opción libre en este gym. Puedes esperar o saltarlo hoy.")
    if motivo == "molestia_dolor":
        aviso = " ".join(t for t in (aviso, lesion_service.AVISO_MEDICO) if t)
    return OpcionesReemplazoOut(motivo=motivo, zona=zona if motivo == "molestia_dolor" else None, opciones=opciones,  # type: ignore[arg-type]
                                puede_guardar_lesion=usuario.consentimiento_aceptado, aviso=aviso)


def reemplazar(db: Session, usuario: Usuario, sesion_id: int, se_id: int, datos: ReemplazoIn) -> SesionEntreno:
    """Cambia el ejercicio SOLO en esta sesión: el plan semanal no se toca (PG-29). Lo ya hecho se conserva: si ya
    hiciste series, ese ejercicio queda cerrado con ellas y el nuevo sigue con las que faltan."""
    s = _en_curso_o_error(db, usuario, sesion_id)
    se = _ejercicio_de(s, se_id)
    if se.cerrado:
        raise ErrorNegocio("Este ejercicio ya se reemplazó.", 409, "ejercicio_cerrado")
    opcion = next((o for o in _opciones(db, usuario, s, se, datos.motivo, datos.zona) if o.id == datos.ejercicio_id), None)
    if opcion is None:  # el backend vuelve a revisar: nada fuera de la lista (equipo y lesiones)
        raise ErrorNegocio("Ese ejercicio no es un reemplazo válido aquí.", 400, "reemplazo_invalido")
    nuevo = db.get(Ejercicio, opcion.id)

    if datos.motivo == "molestia_dolor" and datos.guardar_lesion:
        # PG-22: se guarda como lesión activa (pide consentimiento): el próximo plan ya la tiene en cuenta (PG-20).
        if not any(l.zona.codigo == datos.zona and l.estado in lesion_service.ESTADOS_QUE_LIMITAN for l in usuario.lesiones):
            lesion_service.crear(db, usuario, LesionIn(
                zona=datos.zona, tipo="aguda", duele_con_carga=True, estado="activa",
                descripcion=f"Molestia durante {se.ejercicio.nombre.lower()} (registrada en una sesión).",
            ))

    series, rmin, rmax, descanso = se.series, se.reps_min, se.reps_max, se.descanso_seg
    if nuevo.multiarticular != se.ejercicio.multiarticular and s.rutina_dia_id:
        rutina = db.get(Rutina, db.get(RutinaDia, s.rutina_dia_id).rutina_id)
        if usuario.objetivo and usuario.objetivo.nivel:
            series, rmin, rmax, descanso = reglas.prescripcion(rutina.objetivo_tipo, usuario.objetivo.nivel, nuevo.multiarticular)
    hechas = len(se.series_hechas)
    nota = f"{TEXTO_MOTIVO[datos.motivo]}: {se.ejercicio.nombre}. Solo cambia hoy; tu plan semanal sigue igual."
    if hechas == 0:
        destino = se
        destino.reemplaza_id = se.reemplaza_id or se.ejercicio_id
    else:
        se.cerrado = True
        se.series = hechas
        for otro in s.ejercicios:
            if otro.orden > se.orden:
                otro.orden += 1
        destino = SesionEjercicio(orden=se.orden + 1, rutina_ejercicio_id=se.rutina_ejercicio_id, reemplaza_id=se.ejercicio_id)
        s.ejercicios.append(destino)
        series = max(1, series - hechas)
    destino.ejercicio_id, destino.ejercicio = nuevo.id, nuevo
    destino.gym_maquina_id = _gym_maquina_id(_gym(db, s), nuevo)
    destino.series, destino.reps_min, destino.reps_max, destino.descanso_seg = series, rmin, rmax, descanso
    destino.motivo, destino.nota, destino.precaucion = datos.motivo, nota, opcion.precaucion
    db.commit()
    db.refresh(s)
    return s


# ---------------- PG-37: finalizar y calificar ----------------
def _totales(s: SesionEntreno) -> tuple[int, int, float]:
    planeadas = sum(e.series for e in s.ejercicios)
    hechas = sum(min(len(e.series_hechas), e.series) for e in s.ejercicios)
    volumen = sum(x.peso_kg * x.repeticiones for e in s.ejercicios for x in e.series_hechas)
    return hechas, planeadas, round(volumen, 1)


def _calificar(s: SesionEntreno, fin: datetime) -> None:
    """PG-37: completa = al menos 80 % de las series y un tiempo coherente (no menos del 40 % del estimado).
    Solo la completa cuenta para la asistencia. La parcial también queda guardada en el historial."""
    cfg = get_settings()
    hechas, planeadas, _ = _totales(s)
    duracion = max(0, int((fin - s.inicio_at).total_seconds()))
    completa = planeadas > 0 and hechas / planeadas >= cfg.sesion_pct_completa \
        and duracion >= s.duracion_estimada_seg * cfg.sesion_tiempo_min_pct
    s.fin_at = fin
    s.estado = "completa" if completa else "parcial"
    s.cuenta_asistencia = completa


def finalizar(db: Session, usuario: Usuario, sesion_id: int) -> SesionEntreno:
    s = obtener(db, usuario, sesion_id)
    if s.estado != "en_curso":
        return s  # tocar "Finalizar" dos veces (o con mala señal) no cambia nada
    _calificar(s, ahora())
    db.commit()
    return s


def _calificar_manual(s: SesionEntreno) -> None:
    """PG-39: lo que se registra a mano después queda como "manual". Cuenta para la asistencia si llega al mismo
    porcentaje de series que una sesión completa (no se exige tiempo: no hubo cronómetro)."""
    hechas, planeadas, _ = _totales(s)
    s.estado = "manual"
    s.cuenta_asistencia = planeadas > 0 and hechas / planeadas >= get_settings().sesion_pct_completa


def completar_con_plan(db: Session, usuario: Usuario, sesion_id: int) -> SesionEntreno:
    """PG-39 "Olvidé marcar series": completa una sesión PARCIAL con lo planeado. Cada serie que falta se llena con el
    último peso que marcaste hoy en ese ejercicio (o el peso sugerido, si no marcaste ninguna) y el mínimo de
    repeticiones del plan. Esas series nunca cuentan como récord: no se midieron."""
    s = obtener(db, usuario, sesion_id)
    if s.estado != "parcial":
        raise ErrorNegocio("Solo se puede completar una sesión parcial.", 409, "no_parcial")
    if s.fin_at is None or s.fin_at < ahora() - timedelta(hours=HORAS_PARA_COMPLETAR):
        raise ErrorNegocio(f"Solo se puede completar hasta {HORAS_PARA_COMPLETAR} horas después de terminarla.",
                           409, "fuera_de_plazo")
    abiertos = [se for se in s.ejercicios if not se.cerrado]
    sugeridos = pesos_service.sugerir(db, usuario, [
        pesos_service.Pedido(se.ejercicio, se.reps_min, se.reps_max, se.precaucion) for se in abiertos if not se.series_hechas
    ], s.fecha)
    for se in abiertos:
        hechos = {x.numero_serie for x in se.series_hechas}
        ultima = se.series_hechas[-1] if se.series_hechas else None
        sugerido = sugeridos.get(se.ejercicio_id)
        peso = ultima.peso_kg if ultima else sugerido.peso_kg if sugerido else 0.0
        for n in range(1, se.series + 1):
            if n not in hechos:
                se.series_hechas.append(SerieRegistrada(numero_serie=n, peso_kg=peso, repeticiones=se.reps_min,
                                                        es_record=False, completada_at=s.fin_at))
    _calificar_manual(s)
    db.commit()
    db.refresh(s)
    return s


def registrar_pasada(db: Session, usuario: Usuario, datos: SesionPasadaIn) -> SesionEntreno:
    """PG-39 "Registrar entrenamiento pasado": una sesión que hiciste sin anotarla (hasta 7 días atrás). Los
    ejercicios son los de ese día del plan adaptado al gym (no se aceptan otros) y queda como "manual"."""
    hoy = ahora().date()
    # +1 día: el celular puede ir adelantado respecto de la hora del servidor (UTC).
    if not hoy - timedelta(days=DIAS_ATRAS_PASADA) <= datos.fecha <= hoy + timedelta(days=1):
        raise ErrorNegocio(f"Solo puedes registrar entrenamientos de los últimos {DIAS_ATRAS_PASADA} días.", 400, "fecha_invalida")
    repetida = db.scalar(select(SesionEntreno.id).where(
        SesionEntreno.usuario_id == usuario.id, SesionEntreno.fecha == datos.fecha,
        SesionEntreno.dia_semana == datos.dia, SesionEntreno.estado != "en_curso",
    ).limit(1))
    if repetida is not None:  # también evita duplicarla si el pedido llega dos veces
        raise ErrorNegocio("Ya registraste ese día del plan en esa fecha.", 409, "ya_registrada")

    sesion_dia = _sesion_del_dia(db, usuario, datos.gym_id, datos.dia, hoy)
    duracion = sesion_dia.minutos_estimados * 60
    # Sin hora real: se ubica al mediodía de ese día (así el historial y los récords quedan en orden).
    inicio = datetime.combine(datos.fecha, time(12)) if datos.fecha < hoy else ahora() - timedelta(seconds=duracion)
    s, _ = _congelar(db, usuario, sesion_dia, datos.fecha, inicio)
    por_ejercicio = {se.ejercicio_id: se for se in s.ejercicios}
    for e in datos.ejercicios:
        se = por_ejercicio.get(e.ejercicio_id)
        if se is None:
            raise ErrorNegocio("Ese ejercicio no es parte de ese día en este gym.", 400, "ejercicio_invalido")
        if len(e.series) > se.series + 3:  # las mismas 3 series extra que en vivo
            nombre = db.get(Ejercicio, se.ejercicio_id).nombre
            raise ErrorNegocio(f"{nombre}: como máximo {se.series + 3} series.", 400)
        for n, x in enumerate(e.series, start=1):
            se.series_hechas.append(SerieRegistrada(numero_serie=n, peso_kg=progresion.redondear(x.peso_kg),
                                                    repeticiones=x.repeticiones, completada_at=inicio + timedelta(minutes=n)))
    if not any(se.series_hechas for se in s.ejercicios):
        raise ErrorNegocio("Marca al menos una serie.", 400, "sin_series")
    s.fin_at = inicio + timedelta(seconds=duracion)
    db.add(s)
    db.flush()
    for eid in {se.ejercicio_id for se in s.ejercicios if se.series_hechas}:
        _recalcular_records(db, usuario, s, eid)
    _calificar_manual(s)
    db.commit()
    db.refresh(s)
    return s


def descartar(db: Session, usuario: Usuario, sesion_id: int) -> None:
    """Empezaste por error: se borra la sesión en curso (una terminada no se borra desde aquí)."""
    s = obtener(db, usuario, sesion_id)
    if s.estado != "en_curso":
        raise ErrorNegocio("Solo se puede descartar una sesión en curso.", 409, "sesion_terminada")
    db.delete(s)
    db.commit()


# ---------------- Respuestas ----------------
def _min_seg(seg: int) -> str:
    return f"{seg // 60} min" if seg >= 60 else f"{seg} s"


def _resumen(s: SesionEntreno) -> ResumenOut:
    hechas, planeadas, volumen = _totales(s)
    duracion = int((s.fin_at - s.inicio_at).total_seconds()) if s.fin_at else 0
    pct = round(100 * hechas / planeadas) if planeadas else 0
    records = [RecordOut(ejercicio=e.ejercicio.nombre, peso_kg=x.peso_kg, repeticiones=x.repeticiones)
               for e in s.ejercicios for x in e.series_hechas if x.es_record]
    if s.estado == "completa":
        mensaje = f"¡Sesión completa! Hiciste {hechas} de {planeadas} series en {_min_seg(duracion)}."
    elif s.estado == "manual":
        mensaje = (f"Registrada a mano: {hechas} de {planeadas} series. "
                   + ("Cuenta para tu asistencia." if s.cuenta_asistencia else "Se guardó en tu historial, aunque no "
                      "cuenta como sesión completa."))
    else:
        mensaje = (f"Marcaste {hechas} de {planeadas} series ({_min_seg(duracion)}). Se guardó todo tu avance en el "
                   "historial, aunque no cuenta como sesión completa.")
        if s.cerrada_auto:
            mensaje += " La cerramos sola porque quedó abierta muchas horas."
    return ResumenOut(
        estado=s.estado, cuenta_asistencia=s.cuenta_asistencia, duracion_seg=duracion,  # type: ignore[arg-type]
        duracion_estimada_seg=s.duracion_estimada_seg, series_hechas=hechas, series_planeadas=planeadas, porcentaje=pct,
        volumen_kg=volumen, records=records, mensaje=mensaje,
    )


def a_out(db: Session, usuario: Usuario, s: SesionEntreno) -> SesionOut:
    grupos = plan_service.nombres_grupos(db)
    # Sprint 5 (PG-41/PG-42): el peso para hoy, solo mientras entrenas.
    sugerencias = pesos_service.sugerir(db, usuario, [
        pesos_service.Pedido(e.ejercicio, e.reps_min, e.reps_max, e.precaucion) for e in s.ejercicios if not e.cerrado
    ], s.fecha) if s.estado == "en_curso" else {}
    ejercicios = []
    for e in s.ejercicios:
        historial = _historial(db, usuario, e.ejercicio_id, s)
        anterior = [x for ses, x in historial if ses.id == historial[0][0].id] if historial else []
        mejor = _mejor([(x.peso_kg, x.repeticiones) for _, x in historial])
        ejercicios.append(SesionEjercicioOut(
            id=e.id, orden=e.orden, ejercicio=plan_service.ejercicio_breve(e.ejercicio, grupos),
            reemplaza=plan_service.ejercicio_breve(e.reemplaza, grupos) if e.reemplaza else None, motivo=e.motivo,
            nota=e.nota, precaucion=e.precaucion, series=e.series, reps_min=e.reps_min, reps_max=e.reps_max,
            descanso_seg=e.descanso_seg, cerrado=e.cerrado,
            hechas=[SerieOut(numero=x.numero_serie, peso_kg=x.peso_kg, repeticiones=x.repeticiones, es_record=x.es_record,
                             completada_at=x.completada_at) for x in e.series_hechas],
            anterior=[SerieAnteriorOut(numero=x.numero_serie, peso_kg=x.peso_kg, repeticiones=x.repeticiones) for x in anterior],
            mejor=MejorMarcaOut(peso_kg=mejor[0], repeticiones=mejor[1]) if mejor else None,
            sugerencia=sugerencias.get(e.ejercicio_id) if not e.cerrado else None,
        ))
    hechas, planeadas, volumen = _totales(s)
    return SesionOut(
        id=s.id, estado=s.estado, fecha=s.fecha, dia=s.dia_semana, enfoque=s.enfoque, gym_id=s.gym_id,  # type: ignore[arg-type]
        gym_nombre=s.gym_nombre, inicio_at=s.inicio_at, fin_at=s.fin_at, ahora=ahora(),
        duracion_estimada_seg=s.duracion_estimada_seg, series_hechas=hechas, series_planeadas=planeadas,
        volumen_kg=volumen, cerrada_auto=s.cerrada_auto, ejercicios=ejercicios,
        resumen=_resumen(s) if s.estado != "en_curso" else None,
    )

