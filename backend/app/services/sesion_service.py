"""Sesión en vivo (Sprint 4): iniciar y congelar (PG-30), cronómetro (PG-34), registrar series (PG-35), récords
(PG-40), máquina ocupada (PG-29), "me molesta" (PG-22) y finalizar con calificación (PG-37).

No usa IA: todo son reglas (rápido, gratis y funciona aunque la IA esté caída). El descanso con sonido (PG-36) vive
en la app; el backend solo le da el descanso de cada ejercicio.
"""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import Ejercicio, Gym, Rutina, RutinaDia, SerieRegistrada, SesionEjercicio, SesionEntreno, Usuario, ZonaLesion
from app.schemas.lesion import LesionIn
from app.schemas.sesion import (
    IniciarSesionIn, MejorMarcaOut, OpcionesReemplazoOut, RecordOut, ReemplazoIn, ResumenOut, SerieAnteriorOut, SerieIn,
    SerieOut, SesionEjercicioOut, SesionOut,
)
from app.services import adaptacion_service, catalogo_service, gym_service, lesion_service, plan_service
from app.services import plan_reglas as reglas
from app.services.errores import ErrorNegocio

TEXTO_MOTIVO = {"maquina_ocupada": "La máquina estaba ocupada", "molestia_dolor": "Te molestaba"}


# ---------------- Consultas ----------------
def _cerrar_olvidadas(db: Session, usuario: Usuario) -> None:
    """Cierra y califica las sesiones vencidas del usuario.

    Si encuentra alguna, confirma la transacción de db, incluidos otros cambios pendientes.
    Si no encuentra sesiones vencidas, no hace commit.
    """
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
    """Devuelve la sesión actual; antes puede cerrar vencidas y confirmar la transacción."""
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
    """Comprueba propiedad y estado; puede cerrar vencidas y confirmar antes de lanzar un error."""
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


def iniciar(db: Session, usuario: Usuario, datos: IniciarSesionIn) -> SesionEntreno:
    actual = en_curso(db, usuario)
    if actual is not None:
        raise ErrorNegocio("Ya tienes una rutina en curso. Termínala antes de empezar otra.", 409, "sesion_en_curso")
    fecha = adaptacion_service.fecha_valida(datos.fecha)
    hoy = adaptacion_service.hoy(db, usuario, gym_id=datos.gym_id, dia=datos.dia, fecha=fecha)
    if not hoy.plan_existe:
        raise ErrorNegocio("Primero arma tu plan semanal.", 400, "sin_plan")
    if hoy.requiere_elegir_gym:
        raise ErrorNegocio("Elige en qué gym estás.", 400, "elegir_gym")
    sesion_hoy = hoy.sesion
    if sesion_hoy is None:
        raise ErrorNegocio("Hoy no toca entrenar según tu plan. Puedes adelantar el siguiente día.", 400, "dia_libre")
    if not sesion_hoy.ejercicios:
        raise ErrorNegocio("No hay ejercicios que puedas hacer hoy en este gym.", 400, "sin_ejercicios")

    gym = db.get(Gym, sesion_hoy.gym_id) if sesion_hoy.gym_id else None
    rutina = plan_service.activa(db, usuario)
    rutina_dia = next((d for d in rutina.dias if d.dia_semana == sesion_hoy.dia), None) if rutina else None
    # Las adaptaciones guardadas antes del Sprint 4 no traen de qué ejercicio del plan salen: se busca por código.
    del_plan = {re.ejercicio.codigo: re.id for re in rutina_dia.ejercicios} if rutina_dia else {}
    s = SesionEntreno(
        usuario_id=usuario.id, gym_id=gym.id if gym else None, gym_nombre=gym.nombre if gym else None,
        rutina_dia_id=rutina_dia.id if rutina_dia else None, dia_semana=sesion_hoy.dia, enfoque=sesion_hoy.enfoque,
        fecha=fecha, inicio_at=ahora(), duracion_estimada_seg=sesion_hoy.minutos_estimados * 60, estado="en_curso",
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
    db.add(s)
    if gym is not None:
        gym.ultimo_uso_at = ahora()  # PG-06: el último gym usado
    db.commit()
    db.refresh(s)
    return s


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

    try:
        if datos.motivo == "molestia_dolor" and datos.guardar_lesion:
            # La lesión se confirma junto con el reemplazo, no antes.
            if not any(l.zona.codigo == datos.zona and l.estado in lesion_service.ESTADOS_QUE_LIMITAN for l in usuario.lesiones):
                lesion_service._preparar_creacion(db, usuario, LesionIn(
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
    except Exception:
        db.rollback()
        raise
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
        ))
    hechas, planeadas, volumen = _totales(s)
    return SesionOut(
        id=s.id, estado=s.estado, fecha=s.fecha, dia=s.dia_semana, enfoque=s.enfoque, gym_id=s.gym_id,  # type: ignore[arg-type]
        gym_nombre=s.gym_nombre, inicio_at=s.inicio_at, fin_at=s.fin_at, ahora=ahora(),
        duracion_estimada_seg=s.duracion_estimada_seg, series_hechas=hechas, series_planeadas=planeadas,
        volumen_kg=volumen, cerrada_auto=s.cerrada_auto, ejercicios=ejercicios,
        resumen=_resumen(s) if s.estado != "en_curso" else None,
    )

