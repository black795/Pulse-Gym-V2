"""PG-18: máquinas propuestas pendientes de revisión.

    python -m app.scripts.propuestas                    # las muestra en pantalla
    python -m app.scripts.propuestas --csv salida.csv   # además las exporta

Las propuestas aparecen cuando, en el Sprint 2, un usuario fotografía una máquina que la IA no reconoce y la encuentra
en internet. La columna «usuarios» se llenará cuando exista el inventario de gyms (Sprint 2); por ahora vale 0.
"""
import argparse
import csv

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import MaquinaPropuesta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="ruta del archivo CSV a crear")
    args = ap.parse_args()

    with SessionLocal() as db:
        filas = [
            {"id": p.id, "nombre_encontrado": p.nombre_encontrado, "foto_url": p.foto_url or "",
             "fuente_url": p.fuente_url or "", "usuarios": 0, "creada": p.created_at.isoformat(timespec="minutes")}
            for p in db.scalars(select(MaquinaPropuesta).where(MaquinaPropuesta.estado == "pendiente").order_by(MaquinaPropuesta.id))
        ]

    if not filas:
        print("No hay máquinas propuestas pendientes.")
    for f in filas:
        print(f"#{f['id']}  {f['nombre_encontrado']}  (usuarios: {f['usuarios']})  foto: {f['foto_url'] or '—'}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as archivo:
            w = csv.DictWriter(archivo, fieldnames=["id", "nombre_encontrado", "foto_url", "fuente_url", "usuarios", "creada"])
            w.writeheader()
            w.writerows(filas)
        print(f"Exportado a {args.csv} ({len(filas)} filas).")


if __name__ == "__main__":
    main()
