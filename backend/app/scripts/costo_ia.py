"""PG-49: costo diario estimado de la IA (para el equipo).

    python -m app.scripts.costo_ia            # últimos 7 días
    python -m app.scripts.costo_ia --dias 30

Muestra, por día (UTC) y por tipo, cuántas llamadas hubo, cuántas fallaron o se rechazaron, los tokens y el costo
estimado con los precios de IA_PRECIO_ENTRADA_USD_MILLON / IA_PRECIO_SALIDA_USD_MILLON. Las "copias" son pedidos
duplicados porque el primero tardaba: su costo real no se conoce (no devolvieron tokens) y no se suma.
"""
import argparse
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import LlamadaIA
from app.services import ia_uso_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Costo diario estimado de la IA")
    parser.add_argument("--dias", type=int, default=7)
    args = parser.parse_args()
    cfg = get_settings()
    desde = ia_uso_service.inicio_del_dia() - timedelta(days=args.dias - 1)
    filas: dict[tuple, dict] = defaultdict(lambda: {"llamadas": 0, "fallas": 0, "entrada": 0, "salida": 0, "costo": 0.0})
    with SessionLocal() as db:
        for l in db.scalars(select(LlamadaIA).where(LlamadaIA.created_at >= desde)):
            f = filas[(l.created_at.date(), l.tipo)]
            f["llamadas"] += 1
            f["fallas"] += l.resultado != "ok"
            f["entrada"] += l.tokens_entrada
            f["salida"] += l.tokens_salida
            f["costo"] += l.costo_usd
    print(f"Tope diario: USD {cfg.ia_costo_tope_diario_usd:.2f} · precios: entrada {cfg.ia_precio_entrada_usd_millon} / "
          f"salida {cfg.ia_precio_salida_usd_millon} USD por millón de tokens\n")
    print(f"{'día':<11} {'tipo':<12} {'llamadas':>8} {'no ok':>6} {'tokens entrada':>15} {'tokens salida':>14} {'USD':>9}")
    totales: dict = defaultdict(float)
    for (dia, tipo), f in sorted(filas.items()):
        print(f"{dia!s:<11} {tipo:<12} {f['llamadas']:>8} {f['fallas']:>6} {f['entrada']:>15} {f['salida']:>14} {f['costo']:>9.4f}")
        totales[dia] += f["costo"]
    print()
    for dia, total in sorted(totales.items()):
        aviso = "  ← SUPERA EL TOPE" if total > cfg.ia_costo_tope_diario_usd else ""
        print(f"{dia}: USD {total:.4f}{aviso}")
    if not filas:
        print("Sin llamadas a la IA en ese período.")


if __name__ == "__main__":
    main()
