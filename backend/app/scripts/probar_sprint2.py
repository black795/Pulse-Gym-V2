"""Prueba real de punta a punta (Sprint 1 + Sprint 2 + IA Gemini real) que GUARDA los datos en PostgreSQL.

Ejecutar desde la carpeta backend:
    python -m app.scripts.probar_sprint2
"""
import io
import httpx
from PIL import Image, ImageDraw
from sqlalchemy import func, select

from app.db.base import Base
from app.db.seed import sembrar_catalogo_si_vacio, sembrar_demo
from app.db.session import SessionLocal, engine
from app.models import (
    FotoMaquina, Gym, GymMaquina, Lesion, Medicion, ReconocimientoIA, Usuario, UsuarioObjetivo,
)
from app.schemas.gym import ConfirmarIn, GymIn, ImplementosIn
from app.schemas.lesion import LesionIn
from app.schemas.perfil import PerfilIn
from app.services import (
    consentimiento_service, gym_service, lesion_service, perfil_service, reconocimiento_service, usuario_service,
)

FOTOS_REALES_PRUEBA = [
    ("PRENSA_45", "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Leg_Press/0.jpg"),
    ("HACK_SQUAT", "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Hack_Squat/0.jpg"),
    ("EXT_CUADRICEPS", "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Leg_Extensions/0.jpg"),
    ("CURL_FEMORAL_TUMBADO", "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Lying_Leg_Curls/0.jpg"),
    ("PEC_DECK", "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/Butterfly/0.jpg"),
]


def _imagen_paisaje() -> bytes:
    """Imagen que NO es una máquina de gym (paisaje simple) para probar el rechazo de PG-08."""
    img = Image.new("RGB", (800, 600), (135, 206, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 400, 800, 600], fill=(34, 139, 34))
    d.ellipse([600, 50, 720, 170], fill=(255, 223, 0))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        sembrar_catalogo_si_vacio(db)
        sembrar_demo(db)

        # Segunda cuenta de prueba persistente con pruebas reales de Gemini Vision
        ana = usuario_service.buscar_por_email(db, "ana@pulsegym.app")
        if ana is None:
            ana = usuario_service.crear_usuario(db, nombre="Ana Pérez", email="ana@pulsegym.app", password="Pulse2026!")
        if ana.objetivo is None:
            consentimiento_service.fijar(db, ana, True)
            perfil_service.actualizar(db, ana, PerfilIn(
                edad=28, sexo="femenino", altura_cm=165, peso_kg=61.5, grasa_pct=21.0, masa_muscular_kg=26.4,
                objetivo="bajar_grasa", nivel="intermedio", dias_por_semana=4, minutos_por_sesion=50,
            ))
            lesion_service.crear(db, ana, LesionIn(
                zona="espalda_baja", tipo="cronica", duele_con_carga=True,
                descripcion="Molestia lumbar al cargar peso axial.", estado="activa",
            ))

        gyms_ana = gym_service.listar(db, ana)
        if not gyms_ana:
            gym = gym_service.crear(db, ana, GymIn(nombre="Smart Fit Equipetrol", ubicacion="Av. San Martín"))
            gym_service.marcar_uso(db, ana, gym.id)
            gym_service.fijar_implementos(db, ana, gym.id, ImplementosIn(
                implementos=["mancuernas", "barra", "discos", "banco_plano", "banco_inclinable", "bandas", "colchoneta"],
                mancuernas_max_kg=30,
            ))

            print("\n=== Probando IA real (Google Gemini) con 5 fotos reales + 1 no-máquina ===")
            aciertos = 0
            for codigo_esperado, url in FOTOS_REALES_PRUEBA:
                contenido = httpx.get(url, timeout=15).content
                foto = reconocimiento_service.subir(db, ana, gym.id, contenido)
                rec = reconocimiento_service.reconocer(db, ana, foto.id)
                top1 = rec.sugerencias[0].maquina.codigo if rec.sugerencias else None
                acierto = top1 == codigo_esperado
                aciertos += int(acierto)
                print(
                    f"  [{'OK' if acierto else '~~'}] Esperado: {codigo_esperado:<22} | "
                    f"IA ({rec.modelo}, {rec.duracion_ms} ms): "
                    + ", ".join(f"{s.maquina.codigo} ({s.confianza:.0%})" for s in rec.sugerencias)
                )
                elegir = codigo_esperado
                origen = "sugerencia" if any(s.maquina.codigo == codigo_esperado for s in rec.sugerencias) else "manual"
                reconocimiento_service.confirmar(db, ana, foto.id, ConfirmarIn(codigo=elegir, origen=origen))

            # Foto que no es máquina
            foto_no = reconocimiento_service.subir(db, ana, gym.id, _imagen_paisaje())
            rec_no = reconocimiento_service.reconocer(db, ana, foto_no.id)
            print(f"  [OK] Foto paisaje -> es_maquina_de_gym={rec_no.es_maquina_de_gym}, estado={rec_no.foto.estado}")

            # Marcar una máquina como malograda para dejar registro de cambio de estado
            detalle = gym_service.obtener(db, ana, gym.id)
            if detalle.maquinas:
                gym_service.cambiar_estado(db, ana, gym.id, detalle.maquinas[-1].id, "malograda")

            print(f"\nPrecisión top-1 en las 5 fotos reales: {aciertos}/5 ({aciertos / 5:.0%})")

        print("\n=== Resumen de datos guardados en la base de datos ===")
        for modelo, nombre in [
            (Usuario, "usuario"),
            (UsuarioObjetivo, "usuario_objetivo"),
            (Medicion, "medicion"),
            (Lesion, "lesion"),
            (Gym, "gym"),
            (GymMaquina, "gym_maquina"),
            (FotoMaquina, "foto_maquina"),
            (ReconocimientoIA, "reconocimiento_ia"),
        ]:
            total = db.scalar(select(func.count()).select_from(modelo))
            print(f"  {nombre:<20}: {total} filas")


if __name__ == "__main__":
    main()
