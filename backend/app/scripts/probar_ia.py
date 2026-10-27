"""PG-08: mide qué tan bien reconoce la IA con fotos REALES de tu gym.

Arma una carpeta con una subcarpeta por máquina, nombrada con el código del catálogo:

    fotos_prueba/
      PRENSA_45/        foto1.jpg  foto2.jpg
      HACK_SQUAT/       img_001.heic
      NO_ES_MAQUINA/    selfie.jpg          ← fotos que NO son máquinas (la IA debería rechazarlas)

y corre (desde la carpeta backend):

    python -m app.scripts.probar_ia fotos_prueba
    python -m app.scripts.probar_ia fotos_prueba --csv resultados.csv

Meta del tablero: la primera sugerencia acierta en al menos 80% de un set de 30 fotos reales, en menos de 10 s.
Usa la IA configurada en .env (IA_PROVEEDOR / GEMINI_API_KEY). La capa gratuita de Gemini permite pocas
consultas por minuto: el script espera entre foto y foto (--pausa).
"""
import argparse
import csv
import sys
import time
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services import catalogo_service, fotos_storage, ia_vision
from app.services.errores import ErrorNegocio

EXTENSIONES = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}
NO_ES = "NO_ES_MAQUINA"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", type=Path)
    ap.add_argument("--csv", type=Path, help="guardar el detalle en un CSV")
    ap.add_argument("--pausa", type=float, default=4.0, help="segundos entre fotos (límite gratuito de la IA)")
    args = ap.parse_args()

    with SessionLocal() as db:
        catalogo = [
            ia_vision.MaquinaParaIA(codigo=m.codigo, nombre=m.nombre, otros_nombres=list(m.otros_nombres or []), tipo=m.tipo)
            for m in catalogo_service.maquinas_activas(db)
        ]
    codigos = {m.codigo for m in catalogo}
    fotos = sorted(p for p in args.carpeta.glob("*/*") if p.suffix.lower() in EXTENSIONES)
    if not fotos:
        sys.exit(f"No hay fotos en subcarpetas de {args.carpeta}. Mira las instrucciones: python -m app.scripts.probar_ia -h")
    raras = {p.parent.name for p in fotos} - codigos - {NO_ES}
    if raras:
        sys.exit(f"Estas carpetas no son códigos del catálogo: {', '.join(sorted(raras))}")

    print(f"IA: {get_settings().ia_proveedor_efectivo} ({get_settings().gemini_modelo}) · {len(fotos)} fotos\n")
    filas = []
    for i, p in enumerate(fotos):
        esperado = p.parent.name
        fila = {"foto": str(p), "esperado": esperado, "sugerencias": "", "top1": False, "top3": False, "segundos": "", "error": ""}
        try:
            r = ia_vision.reconocer(fotos_storage.procesar(p.read_bytes()), catalogo)
            sugeridas = [c for c, _ in r.sugerencias]
            fila["sugerencias"] = " ".join(f"{c}:{conf:.2f}" for c, conf in r.sugerencias) or ("(no es máquina)" if not r.es_maquina_de_gym else "(vacío)")
            fila["segundos"] = round(r.duracion_ms / 1000, 1)
            if esperado == NO_ES:
                fila["top1"] = fila["top3"] = not r.es_maquina_de_gym
            else:
                fila["top1"] = sugeridas[:1] == [esperado]
                fila["top3"] = esperado in sugeridas
        except (ia_vision.ErrorIA, ErrorNegocio) as e:
            fila["error"] = str(e)
        filas.append(fila)
        marca = "✓" if fila["top1"] else ("~" if fila["top3"] else "✗")
        segundos = "-" if fila["segundos"] == "" else fila["segundos"]
        print(f"{marca} {esperado:<22} {fila['sugerencias'] or fila['error']}  ({segundos} s)")
        if i < len(fotos) - 1:
            time.sleep(args.pausa)

    n = len(filas)
    tiempos = [f["segundos"] for f in filas if f["segundos"] != ""]
    top1 = sum(f["top1"] for f in filas)
    print(f"\nAcierta la 1.ª sugerencia: {top1}/{n} = {top1 / n:.0%}  (meta: 80%)")
    print(f"Está entre las 3 sugerencias: {sum(f['top3'] for f in filas)}/{n}")
    print(f"Errores de la IA: {sum(1 for f in filas if f['error'])}")
    if tiempos:
        print(f"Tiempo: promedio {sum(tiempos) / len(tiempos):.1f} s · máximo {max(tiempos):.1f} s · más de 10 s: {sum(t > 10 for t in tiempos)}")

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0]))
            w.writeheader()
            w.writerows(filas)
        print(f"Detalle guardado en {args.csv}")


if __name__ == "__main__":
    main()
