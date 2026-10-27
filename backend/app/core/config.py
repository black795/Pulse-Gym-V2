"""Configuración central. Todo lo que cambia entre tu laptop y producción vive aquí."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

CLAVE_POR_DEFECTO = "cambia-esta-clave-en-produccion-ya"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entorno: str = "desarrollo"  # "desarrollo" | "produccion"
    database_url: str = "sqlite:///./pulse_gym.db"
    secret_key: str = CLAVE_POR_DEFECTO
    bcrypt_rounds: int = 12  # costo del hash; más alto = más seguro y más lento
    cors_origins: str = "http://localhost:5173"
    url_app: str = "http://localhost:5173"  # para armar enlaces dentro de los correos

    # PG-01: la sesión dura 30 días en el celular (o hasta que el usuario cierre sesión).
    sesion_dias: int = 30
    # PG-01: 5 intentos fallidos seguidos → bloqueo de 15 minutos.
    login_max_intentos: int = 5
    login_bloqueo_minutos: int = 15
    # PG-01: el enlace de recuperación vence a los 30 minutos y se usa una sola vez.
    recuperacion_minutos: int = 30

    seed_demo: bool = True
    seed_datos_completos: bool = True
    demo_email: str = "demo@pulsegym.app"
    demo_password: str = "Pulse2026!"

    # Correo
    correo_modo: str = "consola"  # "consola" (imprime) | "smtp" (envía)
    correo_remitente: str = "Pulse Gym <no-responder@pulsegym.app>"
    smtp_host: str = ""
    smtp_puerto: int = 587
    smtp_usuario: str = ""
    smtp_password: str = ""

    # PG-06: máximo de gyms por usuario en el MVP.
    gyms_max: int = 5

    # PG-07 / PG-48: fotos de máquinas. Se guardan fuera de cualquier carpeta pública y solo se ven con un
    # enlace firmado que vence (máximo 60 minutos).
    fotos_dir: str = "./uploads/fotos"
    foto_max_mb: int = 10
    foto_max_px: int = 1280
    foto_enlace_minutos: int = 60

    # PG-08: IA con visión. "auto" = Gemini si hay clave; si no, una IA simulada para probar el flujo sin internet.
    ia_proveedor: str = "auto"  # "auto" | "gemini" | "replicate" | "simulada"
    gemini_api_key: str = ""
    gemini_modelo: str = "gemini-flash-lite-latest"
    ia_timeout_seg: float = 15.0
    # Respaldo si Gemini falla o tarda: Gemini 2.5 Flash en Replicate (cobra por tokens; acepta texto e imágenes).
    # IA_PROVEEDOR=replicate usa solo Replicate.
    replicate_api_token: str = ""
    replicate_modelo: str = "google/gemini-2.5-flash"
    # PG-09: desde esta confianza el usuario solo confirma; por debajo elige entre 2–3 parecidas.
    umbral_confianza_alta: float = 0.85

    # PG-23 / PG-26: el plan se arma en menos de 20 s. Si la IA no termina a tiempo, se usa el plan de solo reglas.
    plan_tiempo_max_seg: float = 18.0
    plan_ia_reintentos: int = 2  # PG-26: máximo 2 reintentos con la IA antes de usar la versión de solo reglas
    plan_regeneraciones_dia: int = 3  # PG-23: el usuario puede pedir regenerar su plan hasta 3 veces al día
    # Si un pedido a la IA no volvió en estos segundos, se lanza una copia y se usa la que llegue primero
    # (la capa gratuita de Gemini a veces tarda 30 s en lo que otras veces hace en 3 s). 0 = desactivado.
    ia_duplicar_tras_seg: float = 6.0
    # PG-28: la adaptación del día tarda menos de 10 s.
    adaptacion_tiempo_max_seg: float = 8.0

    # PG-49: límites de IA por usuario al día. Al llegar al límite se ofrece el camino sin IA (elegir a mano / reglas).
    ia_limite_fotos_dia: int = 50
    ia_limite_busquedas_web_dia: int = 3
    ia_limite_planes_dia: int = 5
    ia_limite_adaptaciones_dia: int = 30
    # PG-49: precio estimado (USD por millón de tokens) para calcular el costo diario, aunque se use la capa gratuita.
    ia_precio_entrada_usd_millon: float = 0.10
    ia_precio_salida_usd_millon: float = 0.40
    # Precio en Replicate (verifícalo en https://replicate.com/google/gemini-2.5-flash).
    replicate_precio_entrada_usd_millon: float = 0.30
    replicate_precio_salida_usd_millon: float = 2.50
    # PG-49: si el costo estimado del día (todos los usuarios) supera este tope, se avisa al equipo por correo.
    ia_costo_tope_diario_usd: float = 5.0
    ia_alerta_email: str = ""

    @property
    def cors_lista(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ia_proveedor_efectivo(self) -> str:
        if self.ia_proveedor == "auto":
            return "gemini" if self.gemini_api_key or self.replicate_api_token else "simulada"
        # "replicate" usa el mismo camino que Gemini (ia_cliente.pedir_json decide a quién llamar).
        return "gemini" if self.ia_proveedor == "replicate" else self.ia_proveedor

    def validar_para_produccion(self) -> None:
        """Si estás en producción, se niega a arrancar con configuración insegura."""
        if self.entorno == "produccion":
            if self.secret_key == CLAVE_POR_DEFECTO or len(self.secret_key) < 32:
                raise RuntimeError("SECRET_KEY insegura: define una clave aleatoria de 32+ caracteres.")
            if self.seed_demo:
                raise RuntimeError("SEED_DEMO debe ser false en producción (crearía una cuenta de prueba).")
            if self.correo_modo != "smtp":
                raise RuntimeError("CORREO_MODO debe ser 'smtp' en producción (si no, nadie recibe los correos).")


@lru_cache
def get_settings() -> Settings:
    return Settings()
