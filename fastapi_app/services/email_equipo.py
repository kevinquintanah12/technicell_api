# services/email_equipo.py
"""
Envío de correo para Technicell usando Resend (preferido) y fallback SMTP local.
NO guardes claves en este archivo en producción; usa variables de entorno.
"""

import os
import logging
from typing import Optional
from html import escape

import requests

logger = logging.getLogger("email_equipo")
logger.setLevel(logging.DEBUG)  # Cambia a INFO en producción

# ============================
# === CONFIG (leer desde ENV) ===
# ============================
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "Technicell <onboarding@resend.dev>")
SMTP_USE_SSL = str(os.environ.get("SMTP_USE_SSL", "1")).lower() in ("1", "true", "yes")

# Resend API key — **DEBE** venir desde variable de entorno RESEND_API_KEY
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")  # Ej: re_xxx...

# Timeout para conexiones HTTP/SMTP
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
# Envío por Resend (API HTTP)
# -------------------------
def _send_via_resend(to_email: str, subject: str, body_html: str, body_text: str) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no está configurada")

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": SMTP_FROM,
        "to": to_email,
        "subject": subject,
        "html": body_html,
        "text": body_text,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
        if not (200 <= resp.status_code < 300):
            logger.error("Resend API error: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Resend API error: {resp.status_code} - {resp.text}")
        logger.info("Correo enviado via Resend a %s (status %s)", to_email, resp.status_code)
    except requests.RequestException as exc:
        logger.exception("Error comunicándose con Resend API: %s", exc)
        raise RuntimeError(f"Error comunicándose con Resend API: {exc}") from exc


# -------------------------
# Fallback: Envío por SMTP (solo si RESEND no configurado)
# -------------------------
def _send_via_smtp(to_email: str, subject: str, body_html: str, body_text: str) -> None:
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    try:
        if SMTP_USE_SSL:
            logger.debug("Envío SMTP usando SSL %s:%s", SMTP_HOST, SMTP_PORT)
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=DEFAULT_TIMEOUT) as server:
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            logger.debug("Envío SMTP usando STARTTLS %s:%s", SMTP_HOST, SMTP_PORT)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=DEFAULT_TIMEOUT) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        logger.info("Correo enviado via SMTP a %s", to_email)
    except Exception as exc:
        logger.exception("Error al enviar por SMTP: %s", exc)
        raise RuntimeError(f"Error al enviar por SMTP: {exc}") from exc


# -------------------------
# Función pública principal
# -------------------------
def enviar_email_reparacion(
    to_email: str,
    cliente_nombre: str,
    ticket_id: str,
    modelo: str,
    falla: str,
    message_from_front: Optional[str] = None,
) -> None:
    subject, body_html, body_text = _build_messages(cliente_nombre, ticket_id, modelo, falla, message_from_front)

    # Preferir Resend (API) en producción/Render
    if RESEND_API_KEY:
        logger.debug("Usando Resend API para enviar correo a %s", to_email)
        _send_via_resend(to_email=to_email, subject=subject, body_html=body_html, body_text=body_text)
        return

    # Fallback SMTP (local)
    logger.debug("RESEND_API_KEY no configurada — intentando envío por SMTP (fallback)")
    if not SMTP_HOST:
        raise RuntimeError("No hay método de envío configurado (ni RESEND_API_KEY ni SMTP_HOST)")
    _send_via_smtp(to_email=to_email, subject=subject, body_html=body_html, body_text=body_text)


# ============================
# === Helper de prueba ===
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

# EDITA ESTAS VARIABLES AQUÍ (solo para pruebas locales).
# En producción, usa variables de entorno y remueve los secrets del código.
SMTP_HOST = "smtp.gmail.com"                    # ej. smtp.gmail.com
SMTP_PORT = 465                                 # 465 para SSL, 587 para STARTTLS
SMTP_USER = "technicellreparaciones@gmail.com"      # tu usuario SMTP (email)
SMTP_PASSWORD = "pgpk ydyj fgfp njut"          # <-- CAMBIALO por tu app password (NO subir a git)
SMTP_FROM = "Technicell <technicellreparaciones@gmail.com>"  # valor visible en From
SMTP_USE_SSL = True                             # True -> SMTP_SSL (puerto 465). False -> STARTTLS (puerto 587)

# ==========