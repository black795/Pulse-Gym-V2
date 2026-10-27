"""PG-28: elegir el gym y adaptar la sesión del día a sus máquinas.

Las reglas deciden QUÉ ejercicios no se pueden hacer hoy (falta la máquina, está malograda o retirada, o una lesión
lo impide) y QUÉ reemplazos son válidos (mismo músculo, posibles en este gym y seguros: catalogo_service.alternativas).
La IA solo elige entre esos reemplazos y explica por qué; si falla o tarda, se usa el primero de la lista.
El resultado se guarda (adaptacion_dia): si nada cambió, no se vuelve a llamar a la IA (PG-49).
"""
import hashlib
import json
import time
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import AdaptacionDia, Ejercicio, Gym, Rutina, RutinaDia, Usuario
from app.models.plan import DIAS_SEMANA
from app.schemas.plan import EjercicioHoyOut, GymOpcionOut, HoyOut, OmitidoOut, SesionHoyOut, SiguienteDiaOut
from app.services import catalogo_service, gym_service, ia_cliente, ia_uso_service, lesion_service, plan_ia, plan_service
from app.services import plan_reglas as reglas
from app.services.errores import ErrorNegocio
from app.services.ia_cliente import ErrorIA

MAX_OPCIONES = 5


def fecha_valida(fecha: date | None) -> date:
    """La fecha la manda el celular (su día local). Si es absurda, se usa la del servidor."""
    hoy = ahora().date()
    if fecha is None or abs((fecha - hoy).days) > 1:
        return hoy
    return fecha


def _siguiente(rutina: Rutina, dia_hoy: str) -> RutinaDia | None:
    """El próximo día del plan después de hoy (dando la vuelta a la semana)."""
    i = DIAS_SEMANA.index(dia_hoy)
    por_dia = {d.dia_semana: d for d in rutina.dias}
    for k in range(1, 8):
        d = por_dia.get(DIAS_SEMANA[(i + k) % 7])
        if d is not None:
            return d
    return None


def _firma(rutina_dia: RutinaDia, gym: Gym | None, codigos: set[str], zonas: dict[str, str]) -> str:
    datos = {"dia": rutina_dia.id, "gym": gym.id if gym else None, "codigos": sorted(codigos), "zonas": zonas}
    return hashlib.sha256(json.dumps(datos, sort_keys=True).encode()).hexdigest()


def _motivo_regla(e, gym: Gym | None, codigos: set[str], zonas: dict[str, str], nombres_zonas: dict[str, str]) -> str:
    permitido, _, zona = catalogo_service.revisar_lesiones(e, zonas)
    if not permitido:
        return f"Tu lesión de {nombres_zonas.get(zona, zona).lower()} no permite {e.nombre.lower()} por ahora."
    if gym is None:
        return "Sin gym elegido, usamos ejercicios sin equipo."
    if not codigos:
        return "Este gym no tiene máquinas registradas, así que usamos ejercicios sin equipo."
    maquinas = [x.maquina for x in e.maquinas if x.maquina.activa]
    estados = {gm.maquina_id: gm.estado for gm in gym.maquinas}
    for m in maquinas:
        if estados.get(m.id) == "malograda":
            return f"La máquina {m.nombre} está malograda en este gym."
        if estados.get(m.id) == "retirada":
            return f"La máquina {m.nombre} ya no está en este gym."
    return f"Este gym no tiene {reglas.lista([m.nombre for m in maquinas]) or 'el equipo necesario'}."


def adaptar(db: Session, usuario: Usuario, rutina_dia: RutinaDia, gym: Gym | None, fecha: date) -> SesionHoyOut:
    cfg = get_settings()
    codigos = gym_service.codigos_disponibles(gym) if gym else set()
    zonas = lesion_service.zonas_por_estado(usuario)
    firma = _firma(rutina_dia, gym, codigos, zonas)
    guardada = db.scalar(
        select(AdaptacionDia).where(
            AdaptacionDia.usuario_id == usuario.id, AdaptacionDia.rutina_dia_id == rutina_dia.id,
            AdaptacionDia.fecha == fecha, AdaptacionDia.firma == firma,
        ).order_by(AdaptacionDia.id.desc()).limit(1)
    )
    if guardada is not None:
        return SesionHoyOut.model_validate(guardada.resultado)

    inicio = time.perf_counter()
    grupos = plan_service.nombres_grupos(db)
    nombres_zonas = {z: n for z, n in ((l.zona.codigo, l.zona.nombre) for l in usuario.lesiones)}
    usados = {re.ejercicio_id for re in rutina_dia.ejercicios
              if catalogo_service.disponible(re.ejercicio, codigos) and catalogo_service.revisar_lesiones(re.ejercicio, zonas)[0]}
    filas: list[dict] = []  # en orden: {"re", "ejercicio", "opciones", "motivo"}
    omitidos: list[OmitidoOut] = []
    for re in rutina_dia.ejercicios:
        e = re.ejercicio
        permitido, precaucion, _ = catalogo_service.revisar_lesiones(e, zonas)
        if permitido and catalogo_service.disponible(e, codigos):
            filas.append({"re": re, "ejercicio": e, "precaucion": precaucion, "opciones": None, "motivo": None})
            continue
        opciones = [
            a for a in catalogo_service.alternativas(db, e, zonas=zonas, maquinas_disponibles=codigos, limite=20)
            if a.id not in usados
        ][:MAX_OPCIONES]
        motivo = _motivo_regla(e, gym, codigos, zonas, nombres_zonas)
        if not opciones:
            omitidos.append(OmitidoOut(nombre=e.nombre, motivo=f"{motivo} No encontramos un reemplazo seguro en este gym."))
            continue
        usados.add(opciones[0].id)  # se reserva el primero para que dos cambios no elijan el mismo
        filas.append({"re": re, "ejercicio": e, "precaucion": opciones[0].precaucion, "opciones": opciones, "motivo": motivo})

    cambios = [f for f in filas if f["opciones"]]
    origen, modelo, por_que = "reglas", None, {}
    if cambios and ia_uso_service.disponible(db, usuario, "adaptacion"):
        por_que, modelo = _elegir_con_ia(db, usuario, rutina_dia, gym, cambios, grupos, inicio + cfg.adaptacion_tiempo_max_seg)
        origen = "ia" if modelo else "reglas"

    ejercicios: list[EjercicioHoyOut] = []
    for i, f in enumerate(filas, start=1):
        re = f["re"]
        if f["opciones"] is None:
            ejercicios.append(EjercicioHoyOut(
                orden=i, ejercicio=plan_service.ejercicio_breve(f["ejercicio"], grupos), original=None, cambio=False,
                motivo_cambio=None, por_que_reemplazo=None, precaucion=f["precaucion"], series=re.series,
                reps_min=re.reps_min, reps_max=re.reps_max, descanso_seg=re.descanso_seg,
            ))
            continue
        elegido_codigo, frase = por_que.get(f["ejercicio"].codigo, (f["opciones"][0].codigo, None))
        alt = next(a for a in f["opciones"] if a.codigo == elegido_codigo)
        nuevo = db.get(Ejercicio, alt.id)
        grupo = grupos.get(f["ejercicio"].musculo_principal.codigo, "") if f["ejercicio"].musculo_principal else ""
        # Las series se mantienen; si el reemplazo cambia de tipo (ej. de varias articulaciones a una), se respeta
        # el rango del objetivo con la prescripción de reglas para ese tipo.
        series, rmin, rmax, descanso = re.series, re.reps_min, re.reps_max, re.descanso_seg
        if nuevo.multiarticular != f["ejercicio"].multiarticular:
            rutina = db.get(Rutina, rutina_dia.rutina_id)
            series, rmin, rmax, descanso = reglas.prescripcion(rutina.objetivo_tipo, usuario.objetivo.nivel, nuevo.multiarticular)
        ejercicios.append(EjercicioHoyOut(
            orden=i, ejercicio=plan_service.ejercicio_breve(nuevo, grupos),
            original=plan_service.ejercicio_breve(f["ejercicio"], grupos), cambio=True, motivo_cambio=f["motivo"],
            por_que_reemplazo=frase or f"Trabaja el mismo músculo ({grupo.lower()}) con lo que hay en este gym.",
            precaucion=alt.precaucion, series=series, reps_min=rmin, reps_max=rmax, descanso_seg=descanso,
        ))

    avisos = []
    if gym is not None and not codigos:
        avisos.append("Este gym no tiene máquinas registradas: hoy usamos ejercicios sin equipo. Toma fotos de sus máquinas para aprovecharlas.")
    if gym is None:
        avisos.append("No tienes un gym registrado: hoy usamos ejercicios sin equipo.")
    if any(x.precaucion for x in ejercicios):
        avisos.append("Los ejercicios con precaución hazlos suave y detente si sientes dolor.")
    sesion = SesionHoyOut(
        dia=rutina_dia.dia_semana, dia_nombre=reglas.NOMBRES_DIAS[rutina_dia.dia_semana], enfoque=rutina_dia.enfoque,  # type: ignore[arg-type]
        gym_id=gym.id if gym else None, gym_nombre=gym.nombre if gym else None, origen=origen, modelo=modelo,  # type: ignore[arg-type]
        ejercicios=ejercicios, cambios=sum(1 for x in ejercicios if x.cambio), omitidos=omitidos, avisos=avisos,
        sugerir_fotos=gym is not None and not any(gm.estado != "retirada" for gm in gym.maquinas),
        minutos_estimados=reglas.minutos_estimados([
            reglas.EjercicioPlan("", x.series, x.reps_min, x.reps_max, x.descanso_seg) for x in ejercicios
        ]),
        duracion_ms=int((time.perf_counter() - inicio) * 1000),
    )
    db.add(AdaptacionDia(
        usuario_id=usuario.id, gym_id=gym.id if gym else None, rutina_dia_id=rutina_dia.id, fecha=fecha, firma=firma,
        origen=origen, resultado=sesion.model_dump(mode="json"),
    ))
    db.commit()
    return sesion


def _elegir_con_ia(db: Session, usuario: Usuario, rutina_dia: RutinaDia, gym: Gym | None, cambios: list[dict],
                   grupos: dict[str, str], fin: float) -> tuple[dict[str, tuple[str, str]], str | None]:
    """La IA elige un reemplazo de cada lista y lo explica. Lo que elija fuera de la lista se ignora (se usa el de
    reglas). Devuelve ({codigo_original: (codigo_elegido, frase)}, modelo) o ({}, None) si falló."""
    para_ia = [{
        "codigo": f["ejercicio"].codigo, "nombre": f["ejercicio"].nombre, "motivo": f["motivo"],
        "grupo": grupos.get(f["ejercicio"].musculo_principal.codigo, "") if f["ejercicio"].musculo_principal else "",
        "opciones": [{"codigo": o.codigo, "nombre": o.nombre, "categoria": o.categoria_equipo, "precaucion": o.precaucion}
                     for o in f["opciones"]],
    } for f in cambios]
    inicio = time.perf_counter()
    cfg = get_settings()
    # Si la IA tarda, a la mitad del tiempo se lanza una copia (va primero al proveedor de respaldo, si hay).
    duplicar = min(cfg.ia_duplicar_tras_seg, (fin - inicio) / 2) if cfg.ia_duplicar_tras_seg else None
    resultados, copias = ia_cliente.carrera(
        {"adaptacion": lambda limite: plan_ia.proponer_adaptacion(rutina_dia.enfoque, gym.nombre if gym else "sin gym", para_ia, limite)},
        max(fin, inicio + 1.0), duplicar,
    )
    for _ in range(copias):
        ia_uso_service.registrar(db, usuario.id, "adaptacion", modelo=cfg.ia_proveedor_efectivo, resultado="copia",
                                 detalle="copia de un pedido lento (se usó la respuesta que llegó primero)")
    res = resultados["adaptacion"]
    if res.error is not None:
        if not isinstance(res.error, ErrorIA):
            raise res.error
        ia_uso_service.registrar(db, usuario.id, "adaptacion", modelo=cfg.ia_proveedor_efectivo,
                                 resultado="error", detalle=str(res.error), duracion_ms=res.duracion_ms)
        return {}, None
    r, ms = res.respuesta, res.duracion_ms

    validas = {c["codigo"]: {o["codigo"] for o in c["opciones"]} for c in para_ia}
    elegidos: dict[str, tuple[str, str]] = {}
    rechazos: list[str] = []
    tomados: set[str] = set()
    items = r.datos.get("cambios") if isinstance(r.datos, dict) else None
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        original, reemplazo = str(item.get("original", "")), str(item.get("reemplazo", ""))
        if original not in validas or original in elegidos:
            continue
        if reemplazo not in validas[original] or reemplazo in tomados:
            rechazos.append(f"{original}: {reemplazo or '—'} no es un reemplazo válido")
            continue
        tomados.add(reemplazo)
        elegidos[original] = (reemplazo, reglas.lenguaje_simple(reglas._una_frase(str(item.get("motivo", ""))) or ""))
    # Si la IA reutilizó un reemplazo reservado por reglas para otro cambio, ese otro usa el siguiente libre.
    for c in para_ia:
        if c["codigo"] not in elegidos:
            libre = next((o["codigo"] for o in c["opciones"] if o["codigo"] not in tomados), None)
            if libre is None:
                rechazos.append(f"{c['codigo']}: sin reemplazo libre")
                continue
            tomados.add(libre)
            elegidos[c["codigo"]] = (libre, "")
    if items is None:
        rechazos.append("formato JSON inválido")
    ia_uso_service.registrar(db, usuario.id, "adaptacion", modelo=r.modelo, resultado="rechazada" if rechazos else "ok",
                             detalle="; ".join(rechazos) or None, tokens_entrada=r.tokens_entrada,
                             tokens_salida=r.tokens_salida, duracion_ms=ms)
    return elegidos, r.modelo


def hoy(db: Session, usuario: Usuario, *, gym_id: int | None, dia: str | None, fecha: date | None) -> HoyOut:
    fecha = fecha_valida(fecha)
    dia_hoy = DIAS_SEMANA[fecha.weekday()]
    gyms = gym_service.listar(db, usuario)  # primero el último usado
    ultimo = next((g.id for g in gyms if g.ultimo_uso_at is not None), None)
    base = dict(
        fecha=fecha, dia=dia_hoy, dia_nombre=reglas.NOMBRES_DIAS[dia_hoy],
        gyms=[GymOpcionOut(id=g.id, nombre=g.nombre, es_ultimo_usado=g.id == ultimo,
                           maquinas=sum(1 for gm in g.maquinas if gm.estado != "retirada")) for g in gyms],
    )
    rutina = plan_service.vigente(db, usuario)
    if rutina is None:
        return HoyOut(**base, plan_existe=False, es_dia_de_entreno=False, siguiente_dia=None, requiere_elegir_gym=False, sesion=None)

    por_dia = {d.dia_semana: d for d in rutina.dias}
    es_dia = dia_hoy in por_dia
    sig = _siguiente(rutina, dia_hoy)
    siguiente = SiguienteDiaOut(dia=sig.dia_semana, dia_nombre=reglas.NOMBRES_DIAS[sig.dia_semana], enfoque=sig.enfoque) if sig else None  # type: ignore[arg-type]
    if dia is not None and dia not in por_dia:
        raise ErrorNegocio("Ese día no está en tu plan.", 400)
    elegido = dia or (dia_hoy if es_dia else None)
    comun = dict(**base, plan_existe=True, es_dia_de_entreno=es_dia, siguiente_dia=siguiente)
    if elegido is None:  # hoy no toca: la app ofrece adelantar el siguiente día
        return HoyOut(**comun, requiere_elegir_gym=False, sesion=None)

    if gym_id is None:
        if len(gyms) > 1:  # con más de un gym, primero se elige dónde estás
            return HoyOut(**comun, requiere_elegir_gym=True, sesion=None)
        gym = gyms[0] if gyms else None
    else:
        gym = gym_service.obtener(db, usuario, gym_id)
    return HoyOut(**comun, requiere_elegir_gym=False, sesion=adaptar(db, usuario, por_dia[elegido], gym, fecha))
