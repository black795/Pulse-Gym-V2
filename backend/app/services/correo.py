"""Envío de correos. En desarrollo solo se imprimen en la terminal; en producción se envían por SMTP."""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("pulse.correo")

# Los correos "enviados" en modo consola quedan aquí (las pruebas automáticas los leen).
BUZON_DE_PRUEBA: list[dict] = []


def enviar(destino: str, asunto: str, texto: str) -> None:
    cfg = get_settings()
    if cfg.correo_modo != "smtp":
        BUZON_DE_PRUEBA.append({"para": destino, "asunto": asunto, "texto": texto})
        print(f"\n--- CORREO (modo consola) ---\nPara: {destino}\nAsunto: {asunto}\n\n{texto}\n-----------------------------\n")
        return

    msg = EmailMessage()
    msg["From"] = cfg.correo_remitente
    msg["To"] = destino
    msg["Subject"] = asunto
    msg.set_content(texto)
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_puerto, timeout=15) as servidor:
            servidor.starttls()
            if cfg.smtp_usuario:
                servidor.login(cfg.smtp_usuario, cfg.smtp_password)
            servidor.send_message(msg)
    except Exception:  # un correo que falla no debe tumbar la petición del usuario
        log.exception("No se pudo enviar el correo a %s", destino)


def correo_recuperacion(destino: str, nombre: str, enlace: str, minutos: int) -> None:
    enviar(
        destino,
        "Restablece tu contraseña de Pulse Gym",
        f"Hola {nombre},\n\nRecibimos una solicitud para restablecer tu contraseña.\n"
        f"Abre este enlace (sirve una sola vez y vence en {minutos} minutos):\n\n{enlace}\n\n"
        "Si tú no lo pediste, ignora este correo: tu contraseña sigue igual.\n\n— Pulse Gym",
    )


def correo_cuenta_eliminada(destino: str, nombre: str) -> None:
    enviar(
        destino,
        "Eliminamos tu cuenta de Pulse Gym",
        f"Hola {nombre},\n\nTu cuenta y todos tus datos (perfil, mediciones, lesiones y fotos) fueron eliminados.\n"
        "Si no fuiste tú, responde a este correo de inmediato.\n\n— Pulse Gym",
    )
