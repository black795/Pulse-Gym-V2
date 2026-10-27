"""Foto → IA → el usuario confirma o elige → inventario (PG-07, PG-08, PG-09, PG-12)."""
import time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import FotoMaquina, Gym, GymMaquina, MaquinaCatalogo, ReconocimientoIA, Usuario
from app.schemas.gym import ConfirmarIn, ConfirmarOut, FotoOut, ReconocimientoOut, SugerenciaOut
from app.services import catalogo_service, fotos_storage, gym_service, ia_uso_service, ia_vision
from app.services.errores import ErrorNegocio

MSG_YA_EN_INVENTARIO = "Esta máquina ya está en tu gym. ¿Quieres actualizar su foto con la nueva?"


def a_foto_out(f: FotoMaquina) -> FotoOut:
    return FotoOut(
        id=f.id, gym_id=f.gym_id, estado=f.estado, tomada_at=f.tomada_at,
        url=fotos_storage.enlace_temporal(f.id) if f.archivo else "",
    )


def subir(db: Session, usuario: Usuario, gym_id: int, contenido: bytes) -> FotoMaquina:
    gym = gym_service.obtener(db, usuario, gym_id)
    archivo = fotos_storage.guardar(contenido, usuario.id)
    foto = FotoMaquina(gym_id=gym.id, usuario_id=usuario.id, archivo=archivo, estado="pendiente")
    db.add(foto)
    try:
        db.commit()
    except Exception:
        db.rollback()
        fotos_storage.borrar([archivo])
        raise
    db.refresh(foto)
    return foto


def obtener_foto(db: Session, usuario: Usuario, foto_id: int) -> FotoMaquina:
    foto = db.get(FotoMaquina, foto_id)
    if foto is None or foto.usuario_id != usuario.id:  # solo el dueño ve sus fotos (PG-48)
        raise ErrorNegocio("Foto no encontrada.", 404)
    return foto


def _por_codigo(db: Session) -> dict[str, MaquinaCatalogo]:
    return {m.codigo: m for m in catalogo_service.maquinas_activas(db)}


def reconocer(db: Session, usuario: Usuario, foto_id: int) -> ReconocimientoOut:
    """Envía la foto y la lista del catálogo a la IA. Cada intento queda guardado (PG-08)."""
    foto = obtener_foto(db, usuario, foto_id)
    if foto.estado == "confirmada":
        raise ErrorNegocio("Esta foto ya se agregó a tu gym.", 409, "foto_ya_confirmada")
    if not foto.archivo:
        raise ErrorNegocio("Esta foto se descartó. Toma otra.", 410, "foto_descartada")

    ia_uso_service.exigir_disponible(db, usuario, "foto")  # PG-49: máximo 50 fotos con IA al día

    catalogo = _por_codigo(db)
    para_ia = [
        ia_vision.MaquinaParaIA(codigo=m.codigo, nombre=m.nombre, otros_nombres=list(m.otros_nombres or []), tipo=m.tipo)
        for m in catalogo.values()
    ]
    foto.ia_intentos += 1
    inicio = time.perf_counter()
    try:
        r = ia_vision.reconocer(fotos_storage.leer(foto.archivo), para_ia)
    except ia_vision.ErrorIA as e:
        foto.estado, foto.ia_ultimo_error = "error_ia", str(e)[:300]
        ia_uso_service.registrar(
            db, usuario.id, "foto", modelo=get_settings().ia_proveedor_efectivo, resultado="error", detalle=str(e),
            duracion_ms=int((time.perf_counter() - inicio) * 1000),
        )
        db.commit()
        raise ErrorNegocio(
            f"No pudimos reconocer la máquina: {e} Reintenta o elígela a mano del catálogo.", 503, "ia_fallo",
        )
    ia_uso_service.registrar(
        db, usuario.id, "foto", modelo=r.modelo, resultado="ok",
        detalle=f"{r.descartadas} códigos inventados descartados" if r.descartadas else None,
        tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida, duracion_ms=r.duracion_ms,
    )

    for puesto, (codigo, confianza) in enumerate(r.sugerencias, start=1):
        db.add(ReconocimientoIA(
            foto_id=foto.id, intento=foto.ia_intentos, maquina_id=catalogo[codigo].id,
            confianza=round(confianza, 3), puesto=puesto, modelo=r.modelo[:60],
        ))
    umbral = get_settings().umbral_confianza_alta
    alta = bool(r.sugerencias) and r.sugerencias[0][1] >= umbral
    foto.es_maquina_de_gym = r.es_maquina_de_gym
    foto.ia_duracion_ms = r.duracion_ms
    foto.ia_ultimo_error = None
    foto.estado = "no_es_maquina" if not r.es_maquina_de_gym else ("reconocida_alta" if alta else "opciones_sugeridas")
    db.commit()

    principales = catalogo_service.musculos_principales(db)
    en_inventario = {gm.maquina_id for gm in db.get(Gym, foto.gym_id).maquinas}
    return ReconocimientoOut(
        foto=a_foto_out(foto), es_maquina_de_gym=r.es_maquina_de_gym, confianza_alta=alta, umbral_alta=umbral,
        sugerencias=[
            SugerenciaOut(
                puesto=i, confianza=round(c, 3), maquina=gym_service.opcion(catalogo[cod], principales),
                ya_en_inventario=catalogo[cod].id in en_inventario,
            )
            for i, (cod, c) in enumerate(r.sugerencias, start=1)
        ],
        modelo=r.modelo, duracion_ms=r.duracion_ms,
    )


def _puesto_sugerido(foto: FotoMaquina, maquina_id: int) -> int | None:
    """En qué puesto la sugirió la IA en el último intento (None si el usuario la buscó a mano)."""
    ultimo = max((r.intento for r in foto.reconocimientos), default=None)
    return next((r.puesto for r in foto.reconocimientos if r.intento == ultimo and r.maquina_id == maquina_id), None)


def confirmar(db: Session, usuario: Usuario, foto_id: int, datos: ConfirmarIn) -> ConfirmarOut:
    """Única puerta de entrada al inventario: nada entra sin que el usuario lo confirme (PG-09)."""
    foto = obtener_foto(db, usuario, foto_id)
    if foto.estado == "confirmada":
        raise ErrorNegocio("Esta foto ya se agregó a tu gym.", 409, "foto_ya_confirmada")
    if not foto.archivo:
        raise ErrorNegocio("Esta foto se descartó. Toma otra.", 410, "foto_descartada")
    maquina = db.scalar(select(MaquinaCatalogo).where(
        MaquinaCatalogo.codigo == datos.codigo.strip().upper(), MaquinaCatalogo.activa.is_(True),
    ))
    if maquina is None:
        raise ErrorNegocio("Esa máquina no está en el catálogo.", 404)

    existente = db.scalar(select(GymMaquina).where(GymMaquina.gym_id == foto.gym_id, GymMaquina.maquina_id == maquina.id))
    if existente is not None and not datos.reemplazar_foto:
        raise ErrorNegocio(MSG_YA_EN_INVENTARIO, 409, "ya_en_inventario")

    # PG-09: se registra qué eligió el usuario, para calibrar los umbrales.
    foto.eleccion = datos.origen
    foto.elegida_maquina_id = maquina.id
    foto.elegida_puesto = _puesto_sugerido(foto, maquina.id) if datos.origen == "sugerencia" else None
    foto.elegida_at = ahora()
    foto.estado = "confirmada"

    archivo_viejo = None
    if existente is not None:  # PG-12: no se duplica; se actualiza la foto de la que ya estaba
        vieja = existente.foto
        existente.foto_id = foto.id
        if existente.estado == "retirada":  # si la volvió a fotografiar, es que volvió al gym
            gym_service.registrar_estado(existente, "disponible")
        if vieja is not None and vieja.id != foto.id:
            db.flush()
            archivo_viejo = gym_service.descartar_foto(db, vieja)
        gm, accion = existente, "foto_actualizada"
    else:
        gm = GymMaquina(gym_id=foto.gym_id, maquina_id=maquina.id, foto_id=foto.id, historial_estados=[])
        gym_service.registrar_estado(gm, "disponible")
        db.add(gm)
        accion = "agregada"
    try:
        db.commit()
    except IntegrityError:  # dos confirmaciones a la vez de la misma máquina: la restricción única la frena
        db.rollback()
        raise ErrorNegocio(MSG_YA_EN_INVENTARIO, 409, "ya_en_inventario")
    fotos_storage.borrar([archivo_viejo] if archivo_viejo else [])
    db.refresh(gm)
    return ConfirmarOut(accion=accion, gym_maquina=gym_service.a_gym_maquina_out(gm, catalogo_service.musculos_principales(db)))  # type: ignore[arg-type]


def ninguna(db: Session, usuario: Usuario, foto_id: int) -> FotoMaquina:
    """«Ninguna es»: queda para la búsqueda en internet (PG-10, Sprint 5). Mientras tanto se puede buscar a mano."""
    foto = obtener_foto(db, usuario, foto_id)
    if foto.estado == "confirmada":
        raise ErrorNegocio("Esta foto ya se agregó a tu gym.", 409, "foto_ya_confirmada")
    foto.eleccion, foto.elegida_maquina_id, foto.elegida_puesto, foto.elegida_at = "ninguna", None, None, ahora()
    foto.estado = "busqueda_web"
    db.commit()
    return foto


def descartar(db: Session, usuario: Usuario, foto_id: int) -> None:
    foto = obtener_foto(db, usuario, foto_id)
    if foto.estado == "confirmada" and db.scalar(select(GymMaquina.id).where(GymMaquina.foto_id == foto.id)):
        raise ErrorNegocio("Esta foto es de una máquina de tu gym. Quita la máquina del inventario.", 409)
    archivo = gym_service.descartar_foto(db, foto)
    db.commit()
    fotos_storage.borrar([archivo] if archivo else [])
