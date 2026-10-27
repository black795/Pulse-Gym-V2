"""PG-49: que la IA no se vuelva cara ni lenta. Registra cada llamada, aplica los límites diarios por usuario,
estima el costo y avisa al equipo si el costo del día supera el tope."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import ahora
from app.models import LlamadaIA, Rutina, Usuario
from app.services import correo
from app.services.errores import ErrorNegocio

log = logging.getLogger("pulse.ia")

TIPOS = ("foto", "plan", "adaptacion", "busqueda_web")
MENSAJES_LIMITE = {
    "foto": "Llegaste al límite de {n} fotos reconocidas con IA por hoy. Puedes elegir la máquina a mano del catálogo.",
    "busqueda_web": "Llegaste al límite de {n} búsquedas en internet por hoy. Puedes elegir la máquina a mano del catálogo.",
}

# Fecha (UTC) en que ya se avisó al equipo, para no mandar un correo por cada llamada.
# Vive en memoria: si el servidor se reinicia, como mucho se repite un aviso ese día.
_alerta_enviada: datetime | None = None


def inicio_del_dia() -> datetime:
    """Los límites se cuentan por día UTC (en Bolivia, el contador vuelve a cero a las 20:00)."""
    return ahora().replace(hour=0, minute=0, second=0, microsecond=0)


def limite(tipo: str) -> int:
    cfg = get_settings()
    return {
        "foto": cfg.ia_limite_fotos_dia, "plan": cfg.ia_limite_planes_dia,
        "adaptacion": cfg.ia_limite_adaptaciones_dia, "busqueda_web": cfg.ia_limite_busquedas_web_dia,
    }[tipo]


def usadas_hoy(db: Session, usuario_id: int, tipo: str) -> int:
    desde = inicio_del_dia()
    if tipo == "plan":
        # Un plan puede necesitar hasta 3 llamadas (PG-26: 2 reintentos); se cuenta cada plan armado con IA.
        return db.scalar(select(func.count()).select_from(Rutina).where(
            Rutina.usuario_id == usuario_id, Rutina.creada_at >= desde, Rutina.ia_intentos > 0,
        )) or 0
    return db.scalar(select(func.count()).select_from(LlamadaIA).where(
        LlamadaIA.usuario_id == usuario_id, LlamadaIA.tipo == tipo, LlamadaIA.created_at >= desde,
    )) or 0


def disponible(db: Session, usuario: Usuario, tipo: str) -> bool:
    return usadas_hoy(db, usuario.id, tipo) < limite(tipo)


def exigir_disponible(db: Session, usuario: Usuario, tipo: str) -> None:
    """Para fotos y búsquedas: al llegar al límite se corta con un mensaje claro (la app ofrece elegir a mano).
    El plan y la adaptación no cortan: siguen funcionando con solo reglas."""
    n = limite(tipo)
    if usadas_hoy(db, usuario.id, tipo) >= n:
        raise ErrorNegocio(MENSAJES_LIMITE[tipo].format(n=n), 429, "limite_ia")


def costo(tokens_entrada: int, tokens_salida: int, modelo: str = "") -> float:
    cfg = get_settings()
    if modelo.startswith("replicate/"):
        entrada, salida = cfg.replicate_precio_entrada_usd_millon, cfg.replicate_precio_salida_usd_millon
    else:
        entrada, salida = cfg.ia_precio_entrada_usd_millon, cfg.ia_precio_salida_usd_millon
    return (tokens_entrada * entrada + tokens_salida * salida) / 1_000_000


def registrar(
    db: Session, usuario_id: int | None, tipo: str, *, modelo: str, resultado: str, detalle: str | None = None,
    tokens_entrada: int = 0, tokens_salida: int = 0, duracion_ms: int = 0,
) -> LlamadaIA:
    """Guarda la llamada (sin hacer commit: lo hace quien llama, junto con el resto de su trabajo)."""
    llamada = LlamadaIA(
        usuario_id=usuario_id, tipo=tipo, modelo=(modelo or "?")[:60], resultado=resultado,
        detalle=(detalle or None) and detalle[:500], tokens_entrada=tokens_entrada, tokens_salida=tokens_salida,
        costo_usd=round(costo(tokens_entrada, tokens_salida, modelo or ""), 6), duracion_ms=duracion_ms,
    )
    db.add(llamada)
    db.flush()
    revisar_tope(db)
    return llamada


def costo_del_dia(db: Session, dia: datetime | None = None) -> float:
    desde = dia or inicio_del_dia()
    return float(db.scalar(select(func.coalesce(func.sum(LlamadaIA.costo_usd), 0.0)).where(
        LlamadaIA.created_at >= desde, LlamadaIA.created_at < desde + timedelta(days=1),
    )) or 0.0)


def revisar_tope(db: Session) -> None:
    """Si el costo estimado del día supera el tope, avisa al equipo una vez por día."""
    global _alerta_enviada
    cfg = get_settings()
    hoy = inicio_del_dia()
    if _alerta_enviada == hoy:
        return
    total = costo_del_dia(db, hoy)
    if total <= cfg.ia_costo_tope_diario_usd:
        return
    _alerta_enviada = hoy
    texto = (
        f"El costo estimado de la IA hoy ({hoy:%Y-%m-%d}, UTC) es USD {total:.4f} y superó el tope de "
        f"USD {cfg.ia_costo_tope_diario_usd:.2f}.\n\nRevisa el detalle con: python -m app.scripts.costo_ia\n\n— Pulse Gym"
    )
    log.warning("Costo de IA sobre el tope: USD %.4f > %.2f", total, cfg.ia_costo_tope_diario_usd)
    if cfg.ia_alerta_email:
        correo.enviar(cfg.ia_alerta_email, "Pulse Gym: el costo de la IA superó el tope diario", texto)


def resumen_usuario(db: Session, usuario: Usuario) -> dict:
    return {
        "tipos": [{"tipo": t, "usadas": usadas_hoy(db, usuario.id, t), "limite": limite(t)} for t in TIPOS],
        "costo_hoy_usd": round(float(db.scalar(select(func.coalesce(func.sum(LlamadaIA.costo_usd), 0.0)).where(
            LlamadaIA.usuario_id == usuario.id, LlamadaIA.created_at >= inicio_del_dia(),
        )) or 0.0), 6),
    }
