"""Archivos de las fotos de máquinas (PG-07, PG-48).

- Se aceptan JPG, PNG y HEIC de hasta 10 MB. Se re-guardan como JPG de máximo 1280 px y SIN metadatos
  (las fotos del celular traen la ubicación GPS en el EXIF; no la queremos).
- Viven en FOTOS_DIR, que no es una carpeta pública: solo se ven con un enlace firmado que vence (máximo 1 hora).
- Más adelante se puede cambiar por Cloudinary (URLs firmadas) sin tocar el resto: solo cambia este archivo.
"""
import hashlib
import hmac
import io
import time
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.services.errores import ErrorNegocio

try:  # HEIC (fotos de iPhone). Si no está instalado, esas fotos se rechazan con un mensaje claro.
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC_SOPORTADO = True
except ImportError:  # pragma: no cover
    HEIC_SOPORTADO = False

FORMATOS = {"JPEG", "MPO", "PNG", "HEIF", "WEBP"}  # MPO = JPG de algunos celulares con varias capas


def _raiz() -> Path:
    raiz = Path(get_settings().fotos_dir).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def guardar(contenido: bytes, usuario_id: int) -> str:
    """Valida, reduce y guarda la foto. Devuelve la ruta relativa que se guarda en la base."""
    relativa = f"{usuario_id}/{uuid.uuid4().hex}.jpg"
    destino = _raiz() / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(procesar(contenido))
    return relativa


def procesar(contenido: bytes) -> bytes:
    """Valida la imagen y la devuelve como JPG de máximo FOTO_MAX_PX, derecha y sin metadatos."""
    cfg = get_settings()
    if len(contenido) > cfg.foto_max_mb * 1024 * 1024:
        raise ErrorNegocio(f"La foto pesa más de {cfg.foto_max_mb} MB. Prueba con otra.", 413, "foto_muy_grande")
    try:
        img = Image.open(io.BytesIO(contenido))
        formato = img.format
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ErrorNegocio("No pudimos leer esa imagen. Usa una foto JPG, PNG o HEIC.", 415, "foto_invalida")
    if formato not in FORMATOS:
        raise ErrorNegocio("Formato no permitido. Usa una foto JPG, PNG o HEIC.", 415, "foto_invalida")

    img = ImageOps.exif_transpose(img).convert("RGB")  # endereza la foto y quita transparencias
    img.thumbnail((cfg.foto_max_px, cfg.foto_max_px))
    salida = io.BytesIO()
    img.save(salida, "JPEG", quality=85, optimize=True)  # sin exif=… → se descartan los metadatos
    return salida.getvalue()


def ruta(relativa: str) -> Path:
    destino = (_raiz() / relativa).resolve()
    if _raiz() not in destino.parents:  # nunca salir de la carpeta de fotos
        raise ErrorNegocio("Foto no encontrada.", 404)
    return destino


def leer(relativa: str) -> bytes:
    return ruta(relativa).read_bytes()


def borrar(relativas: list[str]) -> None:
    """Borra los archivos (se llama DESPUÉS de confirmar el cambio en la base)."""
    for r in relativas:
        try:
            ruta(r).unlink(missing_ok=True)
        except (OSError, ErrorNegocio):
            pass


# ---------------- Enlaces temporales (PG-48) ----------------
def _firma(foto_id: int, expira: int) -> str:
    clave = get_settings().secret_key.encode("utf-8")
    return hmac.new(clave, f"foto:{foto_id}:{expira}".encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def enlace_temporal(foto_id: int) -> str:
    """URL relativa a la API que sirve la foto durante FOTO_ENLACE_MINUTOS (máximo 60)."""
    minutos = min(get_settings().foto_enlace_minutos, 60)
    expira = int(time.time()) + minutos * 60
    return f"/api/fotos/{foto_id}/imagen?exp={expira}&firma={_firma(foto_id, expira)}"


def firma_valida(foto_id: int, expira: int, firma: str) -> bool:
    return expira >= int(time.time()) and hmac.compare_digest(firma, _firma(foto_id, expira))
