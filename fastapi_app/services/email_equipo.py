# services/email_equipo.py
"""
Envío de correo vía SMTP (pensado para deploy en Railway u otro hosting que permita SMTP).
Configura las variables de entorno en Railway:
- FROM_EMAIL (ej: "Technicell <no-reply@tu-dominio.com>")
- SMTP_HOST
- SMTP_PORT (ej: 587 o 465)
- SMTP_USER
- SMTP_PASSWORD
- SMTP_USE_SSL (opcional: "1"/"true" para usar SSL directo; por defecto se usa STARTTLS si puerto 587)
- EMAIL_TIMEOUT (opcional, en segundos)
"""

import os
import logging
from typing import Optional, Union, Iterable
from html import escape
import ssl
from email.message import EmailMessage

logger = logging.getLogger("email_equipo")
logger.setLevel(logging.INFO)

# -----------------------------
# Configuración desde ENV
# -----------------------------
FROM_EMAIL = os.environ.get("FROM_EMAIL", "Technicell <no-reply@example.com>")
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))  # default 587 (STARTTLS)
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_USE_SSL = str(os.environ.get("SMTP_USE_SSL", "0")).lower() in ("1", "true", "yes")
DEFAULT_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "30"))


def _safe_escape(text: Optional[str]) -> str:
    return escape(text or "")


def _build_messages(cliente_nombre: str, ticket_id: str, modelo: str, falla: str, message_from_front: Optional[str]):
    cliente_nombre_safe = _safe_escape(cliente_nombre or "Cliente")
    ticket_id_safe = _safe_escape(str(ticket_id))
    modelo_safe = _safe_escape(modelo or "")
    falla_safe = _safe_escape(falla or "")
    mensaje_custom = _safe_escape(message_from_front or "")

    subject = "Technicell — Su equipo ha entrado en reparación"

    mensaje_html = ""
    if mensaje_custom:
        mensaje_html = (
            "<div style='margin-top:12px'>"
            "<div class='label'>Mensaje:</div>"
            f"<div class='value' style='font-weight:500;color:#333'>{mensaje_custom}</div>"
            "</div>"
        )

    body_html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Technicell</title>
</head>
<body style="background:#f4f4f6;padding:20px;font-family:Arial">
  <div style="max-width:680px;margin:auto;background:#fff;border-radius:8px;padding:20px">
    <h2 style="color:#6b46c1">Hola {cliente_nombre_safe} 👋</h2>
    <p>Su equipo <strong>{modelo_safe}</strong> ha cambiado al estado:</p>
    <h3 style="color:#fff;background:#6b46c1;display:inline-block;padding:8px 14px;border-radius:20px">
      EN REPARACIÓN
    </h3>
    <hr style="margin:20px 0">
    <p><strong>Ticket:</strong> #{ticket_id_safe}</p>
    <p><strong>Falla reportada:</strong><br>{falla_safe}</p>
    {mensaje_html}
    <p style="margin-top:20px">
      Gracias por su preferencia.<br>
      <strong>Technicell</strong><br>
      Pte. 7 269, Centro, Orizaba
    </p>
  </div>
</body>
</html>
"""

    body_text = f"""Hola {cliente_nombre_safe},

Su equipo {modelo_safe} ha cambiado al estado: EN REPARACIÓN

Ticket: #{ticket_id_safe}
Falla reportada: {falla_safe}

{message_from_front or ""}

Gracias,
Technicell
"""
    return subject, body_html, body_text


# -------------------------
# Envío vía SMTP (solo)
# -------------------------
def _send_via_smtp(
    to_emails: Union[str, Iterable[str]],
    subject: str,
    body_html: str,
    body_text: str,
) -> None:
    """Envía el email vía SMTP. to_emails puede ser string o iterables (lista/tuple)."""
    if not SMTP_HOST:
        raise RuntimeError("No hay configuración SMTP (SMTP_HOST) configurada en el entorno.")

    # Normalizar destinatarios a lista
    if isinstance(to_emails, str):
        to_list = [to_emails]
    else:
        to_list = list(to_emails)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(to_list)
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    try:
        if SMTP_USE_SSL or SMTP_PORT == 465:
            logger.debug("Conectando SMTP vía SSL a %s:%s", SMTP_HOST, SMTP_PORT)
            context = ssl.create_default_context()
            import smtplib

            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=DEFAULT_TIMEOUT, context=context) as server:
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            # STARTTLS flow (puerto típico 587)
            logger.debug("Conectando SMTP y usando STARTTLS a %s:%s", SMTP_HOST, SMTP_PORT)
            import smtplib

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=DEFAULT_TIMEOUT) as server:
                server.ehlo()
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

        logger.info("Correo enviado via SMTP a %s", to_list)
    except Exception as exc:
        logger.exception("Error al enviar por SMTP: %s", exc)
        raise RuntimeError(f"Error al enviar por SMTP: {exc}") from exc


# -------------------------
# Función pública principal
# -------------------------
def enviar_email_reparacion(
    to_email: Union[str, Iterable[str]],
    cliente_nombre: str,
    ticket_id: str,
    modelo: str,
    falla: str,
    message_from_front: Optional[str] = None,
) -> None:
    subject, body_html, body_text = _build_messages(cliente_nombre, ticket_id, modelo, falla, message_from_front)
    logger.debug("Preparando envío SMTP a %s", to_email)
    _send_via_smtp(to_emails=to_email, subject=subject, body_html=body_html, body_text=body_text)


# ============================
# Helper de prueba (solo desarrollo)
# ============================
def test_send():
    try:
        enviar_email_reparacion(
            to_email=os.environ.get("TEST_EMAIL", "tu_correo_de_prueba@ejemplo.com"),
            cliente_nombre="Prueba",
            ticket_id="TEST-123",
            modelo="iPhone X",
            falla="Test de envío",
            message_from_front="Mensaje de prueba desde test_send()",
        )
        print("Envío de prueba: OK")
    except Exception as e:
        print("Envío de prueba: FALLÓ ->", e)


if __name__ == "__main__":
    test_send()
