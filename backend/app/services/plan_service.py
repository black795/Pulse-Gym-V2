"""Plan semanal (PG-20, PG-23 a PG-27): arma el contexto, pide el plan a la IA, lo valida y lo guarda como una versión.

Flujo de `generar`:
1. Las reglas fijan los límites (días, grupos por día, ejercicios permitidos, rangos).
2. La IA elige dentro de esos límites: se le pide en paralelo cada día (más la explicación general). Lo que no pasa
   la validación se le pide de nuevo diciéndole por qué (máximo 2 reintentos); cada rechazo queda registrado con su
   motivo (llamada_ia).
3. Si la IA sigue fallando o se acaba el tiempo (18 s), ese día usa la versión de solo reglas (o todo el plan, si
   la IA no aportó nada válido).
4. El plan final (de la IA o de reglas) se valida SIEMPRE antes de guardarse: el usuario nunca ve uno que no pasó.
"""
import time
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import GrupoMuscular, Rutina, RutinaDia, RutinaEjercicio, Usuario, ZonaLesion
from app.models.plan import DIAS_SEMANA
from app.schemas.plan import EjercicioBreveOut, LesionEscudoOut, PlanEstadoOut, PlanOut, RutinaDiaOut, RutinaEjercicioOut
from app.services import catalogo_service, gym_service, ia_cliente, ia_uso_service, lesion_service, plan_ia, usuario_service
from app.services import plan_reglas as reglas
from app.services.errores import ErrorNegocio
from app.services.ia_cliente import ErrorIA

MIN_SEG_PARA_INTENTO = 2.0  # si queda menos tiempo que esto, no vale la pena otro intento con la IA


def activa(db: Session, usuario: Usuario) -> Rutina | None:
    return db.scalar(
        select(Rutina).where(Rutina.usuario_id == usuario.id, Rutina.estado == "activa").order_by(Rutina.version.desc()).limit(1)
    )


def regeneraciones_hoy(db: Session, usuario: Usuario) -> int:
    return db.scalar(select(func.count()).select_from(Rutina).where(
        Rutina.usuario_id == usuario.id, Rutina.motivo == "regenerar", Rutina.creada_at >= ia_uso_service.inicio_del_dia(),
    )) or 0


def _dias_por_defecto(usuario: Usuario, actual: Rutina | None) -> list[str]:
    n = usuario.objetivo.dias_por_semana if usuario.objetivo and usuario.objetivo.dias_por_semana else 3
    if actual is not None and len(actual.parametros.get("dias", [])) == n:
        return list(actual.parametros["dias"])
    return list(reglas.SUGERENCIA_DIAS[n])


def _firma_perfil(usuario: Usuario) -> dict:
    o = usuario.objetivo
    return {"objetivo": o.objetivo, "nivel": o.nivel, "minutos": o.minutos_por_sesion, "dias_por_semana": o.dias_por_semana}


def contexto(db: Session, usuario: Usuario, dias: list[str]) -> tuple[reglas.Contexto, int]:
    """Arma lo que necesitan las reglas y la IA. Devuelve también cuántos ejercicios se excluyeron por lesiones."""
    o = usuario.objetivo
    zonas = lesion_service.zonas_por_estado(usuario)
    nombres_zonas = {z.codigo: z.nombre for z in db.scalars(select(ZonaLesion))}
    gyms = gym_service.listar(db, usuario)
    # El plan no depende del gym, pero solo usa lo que se puede hacer en ALGUNO de tus gyms (PG-26).
    # Sin gyms registrados todavía, se puede usar todo el catálogo; la adaptación del día lo resuelve.
    codigos: set[str] | None = set().union(*(gym_service.codigos_disponibles(g) for g in gyms)) if gyms else None

    permitidos: dict[str, reglas.EjercicioInfo] = {}
    bloqueados: dict[str, str] = {}
    posibles_por_grupo: Counter = Counter()
    excluidos = 0
    for e in catalogo_service.listar_ejercicios(db):
        principal = e.musculo_principal
        if principal is None:
            continue
        if not catalogo_service.disponible(e, codigos):
            bloqueados[e.codigo] = "no se puede hacer con el equipo de tus gyms"
            continue
        posibles_por_grupo[principal.codigo] += 1
        permitido, precaucion, zona = catalogo_service.revisar_lesiones(e, zonas)
        if not permitido:
            bloqueados[e.codigo] = f"está contraindicado por la lesión de {nombres_zonas.get(zona, zona).lower()}"
            excluidos += 1
            continue
        permitidos[e.codigo] = reglas.EjercicioInfo(
            id=e.id, codigo=e.codigo, nombre=e.nombre, grupo=principal.codigo, multiarticular=e.multiarticular,
            dificultad=e.dificultad, categoria=e.categoria_equipo, precaucion=precaucion,
        )

    med = usuario.mediciones
    perfil = {
        "edad": usuario.edad, "sexo": usuario.sexo,
        "peso_kg": next((m.peso_kg for m in med if m.peso_kg is not None), None),
        "grasa_pct": next((m.grasa_pct for m in med if m.grasa_pct is not None), None),
        "masa_muscular_kg": next((m.masa_muscular_kg for m in med if m.masa_muscular_kg is not None), None),
    }
    ctx = reglas.preparar(reglas.Contexto(
        dias=dias, objetivo=o.objetivo, objetivo_tipo=reglas.OBJETIVO_A_TIPO[o.objetivo], nivel=o.nivel,
        minutos=o.minutos_por_sesion, permitidos=permitidos, bloqueados=bloqueados,
        nombres_grupos={g.codigo: g.nombre for g in db.scalars(select(GrupoMuscular))},
        zonas=zonas, nombres_zonas=nombres_zonas, perfil=perfil, con_equipo=bool(codigos),
    ))
    # PG-20: si no queda ningún ejercicio posible para un grupo, se omite y se avisa.
    for d in ctx.dias:
        for g in reglas.PLANTILLAS[ctx.plantilla_por_dia[d]][1]:
            if g in ctx.grupos_omitidos or any(e.grupo == g for e in permitidos.values()):
                continue
            ctx.grupos_omitidos[g] = (
                "tus lesiones impiden por ahora todos los ejercicios de este grupo." if posibles_por_grupo[g]
                else "no hay equipo para este grupo en tus gyms."
            )
    return ctx, excluidos


@dataclass
class ResultadoIA:
    plan: reglas.PlanPropuesto | None  # None si la IA no aportó nada válido
    origen: str  # ia (todo de la IA) | mixto (algunos días de reglas) | reglas
    modelo: str | None
    rondas: int


def _pedidos(ctx: reglas.Contexto, base: reglas.PlanPropuesto) -> list[plan_ia.Pedido]:
    """Una llamada para la explicación general y una por día, con la propuesta de reglas como punto de partida."""
    pedidos = [plan_ia.Pedido("general")]
    for d in base.dias:
        mismo_enfoque = {o.dia: [e.codigo for e in o.ejercicios] for o in base.dias
                         if o.dia != d.dia and ctx.plantilla_por_dia[o.dia] == ctx.plantilla_por_dia[d.dia]}
        pedidos.append(plan_ia.Pedido(
            "dia", dia=d.dia, base=d, otros=mismo_enfoque,
            # Para que la semana cubra todos los grupos grandes, cada día conserva los que trae la propuesta de reglas.
            obligatorios=[g for g in d.grupos if g in reglas.GRUPOS_GRANDES],
        ))
    return pedidos


def _con_ia(db: Session, usuario: Usuario, ctx: reglas.Contexto, fin: float) -> ResultadoIA:
    """Pide el plan a la IA EN PARALELO (explicación general + un pedido por día) y valida cada respuesta.
    Lo rechazado se vuelve a pedir explicando por qué (máximo 2 reintentos, PG-26) y cada rechazo queda registrado.
    Lo que no llegue válido a tiempo usa la versión de reglas de ese día."""
    cfg = get_settings()
    base = reglas.armar_con_reglas(ctx)
    pendientes = _pedidos(ctx, base)
    dias_ia: dict[str, reglas.DiaPlan] = {}
    general: str | None = None
    modelo: str | None = None
    rondas = 0
    while pendientes and rondas <= cfg.plan_ia_reintentos:
        restante = fin - time.perf_counter()
        if restante < MIN_SEG_PARA_INTENTO:
            break
        rondas += 1
        # Los hilos solo llaman a la IA; la base de datos se toca después, aquí en el hilo principal.
        resultados, copias = ia_cliente.carrera(
            {p.clave: (lambda limite, p=p: plan_ia.proponer(ctx, p, limite)) for p in pendientes}, fin, cfg.ia_duplicar_tras_seg or None,
        )
        for _ in range(copias):
            ia_uso_service.registrar(db, usuario.id, "plan", modelo=cfg.ia_proveedor_efectivo, resultado="copia",
                                     detalle="copia de un pedido lento (se usó la respuesta que llegó primero)")
        siguientes = []
        for pedido in pendientes:
            res = resultados[pedido.clave]
            r, error, ms = res.respuesta, res.error, res.duracion_ms
            if error is not None:  # falla de conexión, límite por minuto o tiempo: reintentar enseguida no lo arregla
                if not isinstance(error, ErrorIA):
                    raise error
                ia_uso_service.registrar(db, usuario.id, "plan", modelo=cfg.ia_proveedor_efectivo, resultado="error",
                                         detalle=f"{pedido.clave}: {error}", duracion_ms=ms)
                continue
            errores: list[str] = []
            correcciones: list[str] = []
            try:
                if pedido.tipo == "general":
                    texto = plan_ia.interpretar_general(r.datos).strip()
                    if not texto:
                        errores.append("explicación general vacía")
                else:
                    dia = plan_ia.interpretar_dia(r.datos, ctx, pedido)
                    reglas.revisar_dia(dia, ctx, errores, correcciones, pedido.obligatorios)
            except plan_ia.ErrorFormato as e:
                errores.append(str(e))
            ia_uso_service.registrar(
                db, usuario.id, "plan", modelo=r.modelo, resultado="rechazada" if errores else "ok",
                detalle=f"{pedido.clave}: " + "; ".join(errores or correcciones) if errores or correcciones else pedido.clave,
                tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida, duracion_ms=ms,
            )
            if errores:  # PG-26: se vuelve a pedir diciéndole a la IA qué estuvo mal
                pedido.errores_previos = errores
                siguientes.append(pedido)
                continue
            modelo = r.modelo
            if pedido.tipo == "general":
                general = texto
            else:
                dias_ia[pedido.dia] = dia
        pendientes = siguientes

    if not dias_ia:
        return ResultadoIA(None, "reglas", None, rondas)
    completo = len(dias_ia) == len(base.dias)
    explicacion = general or base.explicacion
    if not completo:
        explicacion += " Algunos días los armamos con nuestras reglas porque la IA no respondió a tiempo."
    plan = reglas.PlanPropuesto(explicacion=explicacion, dias=[dias_ia.get(d.dia, d) for d in base.dias], avisos=base.avisos)
    return ResultadoIA(plan, "ia" if completo else "mixto", modelo, rondas)


def generar(db: Session, usuario: Usuario, dias: list[str] | None, motivo: str) -> Rutina:
    """motivo: primera | regenerar (lo pide el usuario, máx. 3 al día) | lesion (automático, PG-20)."""
    cfg = get_settings()
    faltan = usuario_service.campos_faltantes(usuario)
    if faltan:
        raise ErrorNegocio("Para armar tu plan completa tu objetivo, nivel, días y minutos por sesión.", 400, "perfil_incompleto")
    actual = activa(db, usuario)
    if actual is None and motivo == "regenerar":
        motivo = "primera"
    if motivo == "regenerar" and regeneraciones_hoy(db, usuario) >= cfg.plan_regeneraciones_dia:
        raise ErrorNegocio(
            f"Ya regeneraste tu plan {cfg.plan_regeneraciones_dia} veces hoy. Podrás hacerlo de nuevo mañana.",
            429, "limite_regeneraciones",
        )
    dias = reglas.ordenar_dias(dias or _dias_por_defecto(usuario, actual))
    if usuario.objetivo.dias_por_semana != len(dias):
        usuario.objetivo.dias_por_semana = len(dias)  # el perfil queda igual a los días elegidos

    inicio = time.perf_counter()
    ctx, excluidos = contexto(db, usuario, dias)
    plan, origen, modelo, intentos, extra = None, "reglas", None, 0, ""
    if ia_uso_service.disponible(db, usuario, "plan"):
        r = _con_ia(db, usuario, ctx, inicio + cfg.plan_tiempo_max_seg)
        intentos = r.rondas
        if r.plan is not None:
            # La semana completa se vuelve a validar (días seguidos, grupos grandes, explicación con la lesión).
            revision = reglas.validar(r.plan, ctx)
            if revision.ok:
                plan, origen, modelo = revision.plan, r.origen, r.modelo
            else:
                ia_uso_service.registrar(db, usuario.id, "plan", modelo=r.modelo or "?", resultado="rechazada",
                                         detalle="semana: " + "; ".join(revision.errores))
        if plan is None:
            extra = "La IA no logró un plan válido a tiempo, así que lo armamos con nuestras reglas de entrenamiento: es igual de seguro."
    else:
        extra = f"Hoy ya armaste {ia_uso_service.limite('plan')} planes con IA; este lo armamos con nuestras reglas de entrenamiento."
    if plan is None:
        revision = reglas.validar(reglas.armar_con_reglas(ctx, extra), ctx)
        if not revision.ok:  # no debería pasar: las reglas arman planes válidos. Si pasa, no se muestra nada inválido.
            raise ErrorNegocio("No pudimos armar un plan seguro con tus datos. Avísanos para revisarlo.", 500, "plan_invalido")
        plan = revision.plan
    plan.avisos = reglas.avisos_generales(ctx) + plan.avisos

    if actual is not None:
        actual.estado = "archivada"
    version = (db.scalar(select(func.max(Rutina.version)).where(Rutina.usuario_id == usuario.id)) or 0) + 1
    rutina = Rutina(
        usuario_id=usuario.id, rutina_anterior_id=actual.id if actual else None, version=version, estado="activa",
        origen=origen, modelo=modelo, ia_intentos=intentos, motivo=motivo, esquema=ctx.esquema,
        objetivo_tipo=ctx.objetivo_tipo, explicacion=plan.explicacion, avisos=plan.avisos,
        parametros={"dias": ctx.dias, "zonas": ctx.zonas, "excluidos": excluidos, **_firma_perfil(usuario)},
        duracion_ms=int((time.perf_counter() - inicio) * 1000),
        dias=[
            RutinaDia(
                dia_semana=d.dia, orden=DIAS_SEMANA.index(d.dia), enfoque=d.enfoque, grupos=d.grupos, explicacion=d.explicacion,
                ejercicios=[
                    RutinaEjercicio(
                        ejercicio_id=ctx.permitidos[e.codigo].id, orden=i, series=e.series, reps_min=e.reps_min,
                        reps_max=e.reps_max, descanso_seg=e.descanso_seg, motivo=e.motivo[:200], precaucion=e.precaucion,
                    )
                    for i, e in enumerate(d.ejercicios, start=1)
                ],
            )
            for d in plan.dias
        ],
    )
    db.add(rutina)
    usuario.plan_requiere_regenerar = False
    db.commit()
    db.refresh(rutina)
    return rutina


def _sigue_siendo_seguro(rutina: Rutina, zonas: dict[str, str]) -> bool:
    """PG-20: el backend vuelve a revisar el plan guardado con las lesiones de HOY (y con el catálogo de hoy)."""
    if rutina.parametros.get("zonas", {}) != zonas:
        return False  # lesión nueva, cambio de estado o recuperada: se regenera
    return all(catalogo_service.revisar_lesiones(re.ejercicio, zonas)[0] for d in rutina.dias for re in d.ejercicios)


def vigente(db: Session, usuario: Usuario) -> Rutina | None:
    """El plan activo, regenerado solo si las lesiones cambiaron (PG-20: una nueva lesión regenera el plan)."""
    rutina = activa(db, usuario)
    if rutina is None or usuario_service.campos_faltantes(usuario):
        return rutina
    if not _sigue_siendo_seguro(rutina, lesion_service.zonas_por_estado(usuario)):
        rutina = generar(db, usuario, rutina.parametros.get("dias"), "lesion")
    return rutina


# ---------------- Respuestas ----------------
def ejercicio_breve(e, nombres_grupos: dict[str, str]) -> EjercicioBreveOut:
    principal = e.musculo_principal
    return EjercicioBreveOut(
        id=e.id, codigo=e.codigo, nombre=e.nombre,
        musculo_principal=nombres_grupos.get(principal.codigo, principal.nombre) if principal else None,
        categoria_equipo=e.categoria_equipo, maquinas=[x.maquina.nombre for x in e.maquinas if x.maquina.activa],
    )


def nombres_grupos(db: Session) -> dict[str, str]:
    return {g.codigo: g.nombre for g in db.scalars(select(GrupoMuscular))}


def a_plan_out(db: Session, rutina: Rutina) -> PlanOut:
    grupos = nombres_grupos(db)
    zonas = {z.codigo: z.nombre for z in db.scalars(select(ZonaLesion))}
    return PlanOut(
        id=rutina.id, version=rutina.version, origen=rutina.origen, modelo=rutina.modelo, motivo=rutina.motivo,  # type: ignore[arg-type]
        esquema=rutina.esquema, esquema_texto=reglas.TEXTO_ESQUEMA.get(rutina.esquema, rutina.esquema),
        objetivo_tipo=rutina.objetivo_tipo, explicacion=rutina.explicacion, avisos=list(rutina.avisos or []),
        lesiones=[LesionEscudoOut(zona=z, nombre=zonas.get(z, z), estado=e) for z, e in rutina.parametros.get("zonas", {}).items()],  # type: ignore[arg-type]
        ejercicios_excluidos=rutina.parametros.get("excluidos", 0), creada_at=rutina.creada_at, duracion_ms=rutina.duracion_ms,
        dias=[
            RutinaDiaOut(
                id=d.id, dia=d.dia_semana, dia_nombre=reglas.NOMBRES_DIAS[d.dia_semana], enfoque=d.enfoque,  # type: ignore[arg-type]
                grupos=[grupos.get(g, g) for g in d.grupos], explicacion=d.explicacion,
                minutos_estimados=reglas.minutos_estimados([
                    reglas.EjercicioPlan("", e.series, e.reps_min, e.reps_max, e.descanso_seg) for e in d.ejercicios
                ]),
                ejercicios=[
                    RutinaEjercicioOut(
                        id=e.id, orden=e.orden, ejercicio=ejercicio_breve(e.ejercicio, grupos), series=e.series,
                        reps_min=e.reps_min, reps_max=e.reps_max, descanso_seg=e.descanso_seg, motivo=e.motivo,
                        precaucion=e.precaucion,
                    )
                    for e in d.ejercicios
                ],
            )
            for d in rutina.dias
        ],
    )


def estado(db: Session, usuario: Usuario, rutina: Rutina | None) -> PlanEstadoOut:
    cfg = get_settings()
    faltan = usuario_service.campos_faltantes(usuario)
    perfil_cambio = False
    if rutina is not None and not faltan:
        p = rutina.parametros
        perfil_cambio = any(p.get(k) != v for k, v in _firma_perfil(usuario).items())
    return PlanEstadoOut(
        plan=a_plan_out(db, rutina) if rutina is not None else None,
        puede_generar=not faltan, faltan=faltan,
        dias_sugeridos=_dias_por_defecto(usuario, rutina) if not faltan else [],  # type: ignore[arg-type]
        regeneraciones_restantes=max(0, cfg.plan_regeneraciones_dia - regeneraciones_hoy(db, usuario)),
        regeneraciones_max=cfg.plan_regeneraciones_dia, perfil_cambio=perfil_cambio,
    )
