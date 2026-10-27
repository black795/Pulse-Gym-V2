"""Datos iniciales. Es seguro ejecutarlo muchas veces: solo crea lo que falta."""
from datetime import timedelta
import io

from PIL import Image, ImageDraw
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import (
    FotoMaquina, Gym, GymMaquina, Lesion, MaquinaCatalogo, MaquinaPropuesta, Medicion, ReconocimientoIA,
    Usuario, UsuarioObjetivo, ZonaLesion,
)
from app.scripts import cargar_catalogo
from app.services import consentimiento_service, fotos_storage, gym_service, usuario_service


def sembrar_catalogo_si_vacio(db: Session) -> None:
    """Si la base está recién creada, carga el catálogo para que la app funcione de una vez.
    Si ya tiene catálogo NO lo toca (así no pisa lo que el equipo haya editado). Para actualizarlo a propósito:
    python -m app.scripts.cargar_catalogo"""
    if db.scalar(select(func.count()).select_from(ZonaLesion)) == 0:
        informe, _ = cargar_catalogo.cargar(db)
        if not informe.ok:
            raise RuntimeError("El catálogo tiene errores: " + " | ".join(informe.errores[:5]))


def _foto_demo(etiqueta: str, color: tuple[int, int, int]) -> bytes:
    """Genera una imagen JPG de ejemplo (sin internet) para las máquinas sembradas."""
    img = Image.new("RGB", (960, 720), color)
    d = ImageDraw.Draw(img)
    d.rectangle([60, 60, 900, 660], outline=(220, 235, 225), width=4)
    d.text((100, 320), f"Pulse Gym - {etiqueta}", fill=(240, 250, 242))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def sembrar_demo(db: Session) -> None:
    cfg = get_settings()
    u = usuario_service.buscar_por_email(db, cfg.demo_email)
    if u is None:
        u = usuario_service.crear_usuario(db, nombre="Usuario Demo", email=cfg.demo_email, password=cfg.demo_password)
    if not cfg.seed_datos_completos:
        return
    # Si la cuenta demo aún no tiene gyms ni perfil completo, siembra datos reales de Sprint 1 y Sprint 2
    # para que se puedan ver en la app y en PostgreSQL / pgAdmin desde el primer arranque.
    if db.scalar(select(func.count()).select_from(Gym).where(Gym.usuario_id == u.id)) > 0:
        return

    hoy = ahora()
    u.consentimiento_estado = "aceptado"
    u.consentimiento_version = consentimiento_service.VERSION_VIGENTE
    u.consentimiento_at = hoy - timedelta(days=14)
    u.edad = 26
    u.sexo = "masculino"
    u.altura_cm = 176.0
    u.descanso_default_seg = 90

    if u.objetivo is None:
        u.objetivo = UsuarioObjetivo(
            objetivo="ganar_musculo", nivel="intermedio", dias_por_semana=4, minutos_por_sesion=60,
        )

    if not u.mediciones:
        db.add_all([
            Medicion(usuario_id=u.id, fecha=(hoy - timedelta(days=14)).date(), peso_kg=73.2, grasa_pct=17.4, masa_muscular_kg=34.5),
            Medicion(usuario_id=u.id, fecha=(hoy - timedelta(days=7)).date(), peso_kg=73.9, grasa_pct=17.0, masa_muscular_kg=34.9),
            Medicion(usuario_id=u.id, fecha=hoy.date(), peso_kg=74.5, grasa_pct=16.6, masa_muscular_kg=35.3),
        ])

    if not u.lesiones:
        zonas = {z.codigo: z.id for z in db.scalars(select(ZonaLesion))}
        if "rodilla" in zonas and "hombro" in zonas:
            db.add_all([
                Lesion(
                    usuario_id=u.id, zona_id=zonas["rodilla"], tipo="cronica", duele_con_carga=True,
                    descripcion="Molestia leve en tendón rotuliano al bajar profundo con mucho peso.",
                    estado="reintroduccion",
                ),
                Lesion(
                    usuario_id=u.id, zona_id=zonas["hombro"], tipo="aguda", duele_con_carga=False,
                    descripcion="Sobrecarga anterior ya recuperada.",
                    estado="recuperada", recuperada_at=hoy - timedelta(days=3),
                ),
            ])

    gym_principal = Gym(
        usuario_id=u.id,
        nombre="Premier Fitness Club",
        ubicacion="Av. América esq. Pando",
        implementos=["mancuernas", "barra", "discos", "banco_plano", "banco_inclinable", "rack", "barra_dominadas", "bandas"],
        mancuernas_max_kg=40.0,
        ultimo_uso_at=hoy,
    )
    gym_casa = Gym(
        usuario_id=u.id,
        nombre="Entreno en Casa",
        ubicacion="Equipamiento propio",
        implementos=["mancuernas", "bandas", "colchoneta", "kettlebell"],
        mancuernas_max_kg=20.0,
        ultimo_uso_at=hoy - timedelta(days=2),
    )
    db.add_all([gym_principal, gym_casa])
    db.flush()

    maquinas = {m.codigo: m for m in db.scalars(select(MaquinaCatalogo))}
    ejemplos = [
        ("PRENSA_45", "disponible", 0.96, [("PRENSA_45", 0.96), ("HACK_SQUAT", 0.18)], (45, 70, 60)),
        ("HACK_SQUAT", "disponible", 0.94, [("HACK_SQUAT", 0.94), ("PRENSA_45", 0.25)], (50, 65, 80)),
        ("EXT_CUADRICEPS", "disponible", 0.93, [("EXT_CUADRICEPS", 0.93), ("CURL_FEMORAL_SENTADO", 0.22)], (60, 55, 75)),
        ("POLEA_ALTA", "disponible", 0.91, [("POLEA_ALTA", 0.91), ("POLEA_CRUZADA", 0.30)], (40, 75, 70)),
        ("PRESS_PECHO_MAQ", "disponible", 0.89, [("PRESS_PECHO_MAQ", 0.89), ("PEC_DECK", 0.28)], (70, 50, 60)),
        ("SMITH", "disponible", 0.92, [("SMITH", 0.92), ("RACK_SENTADILLA", 0.21)], (55, 65, 65)),
        ("CURL_FEMORAL_SENTADO", "malograda", 0.78, [("CURL_FEMORAL_SENTADO", 0.78), ("CURL_FEMORAL_TUMBADO", 0.54)], (80, 55, 50)),
        ("ELIPTICA", "retirada", 0.90, [("ELIPTICA", 0.90), ("BICICLETA_ESTATICA", 0.15)], (60, 60, 60)),
    ]
    for codigo, estado_maq, conf, sugs, color in ejemplos:
        if codigo not in maquinas:
            continue
        m = maquinas[codigo]
        archivo = fotos_storage.guardar(_foto_demo(m.nombre, color), u.id)
        foto = FotoMaquina(
            gym_id=gym_principal.id, usuario_id=u.id, archivo=archivo, estado="confirmada",
            es_maquina_de_gym=True, ia_intentos=1, ia_duracion_ms=2650,
            eleccion="sugerencia", elegida_maquina_id=m.id, elegida_puesto=1, elegida_at=hoy - timedelta(hours=2),
        )
        db.add(foto)
        db.flush()
        for puesto, (cod_sug, conf_sug) in enumerate(sugs, start=1):
            if cod_sug in maquinas:
                db.add(ReconocimientoIA(
                    foto_id=foto.id, intento=1, maquina_id=maquinas[cod_sug].id,
                    confianza=conf_sug, puesto=puesto, modelo=cfg.gemini_modelo,
                ))
        gm = GymMaquina(gym_id=gym_principal.id, maquina_id=m.id, foto_id=foto.id, historial_estados=[])
        gym_service.registrar_estado(gm, "disponible")
        if estado_maq != "disponible":
            gym_service.registrar_estado(gm, estado_maq)
        db.add(gm)

    if db.scalar(select(func.count()).select_from(MaquinaPropuesta)) == 0:
        db.add(MaquinaPropuesta(
            nombre_encontrado="Belt Squat (Sentadilla con cinturón)",
            foto_url="https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Hack_Squat/0.jpg",
            fuente_url="https://exrx.net/WeightExercises/Quadriceps/BWBeltSquat",
            estado="pendiente",
        ))

    db.commit()
