# services/email_equipo.py
"""
Servicio de envío de correo para Technicell.
Este archivo contiene la configuración SMTP **en el mismo archivo** para facilitar pruebas locales.
**ADVERTENCIA:** NO dejes contraseñas aquí en producción ni las subas a GitHub.
Puedes sobrescribir estas variables con variables de entorno si lo prefieres.
"""

import os
import smtplib
import logging
from typing import Optional
from email.message import EmailMessage
from html import escape

logger = logging.getLogger("email_equipo")
logger.setLevel(logging.DEBUG)  # Cambia a INFO en producción

# ============================
# === CONFIGURACIÓN SMTP ====
# ============================
# EDITA ESTAS VARIABLES AQUÍ (solo para pruebas locales).
# En producción, usa variables de entorno y remueve los secrets del código.
SMTP_HOST = "smtp.gmail.com"                    # ej. smtp.gmail.com
SMTP_PORT = 465                                 # 465 para SSL, 587 para STARTTLS
SMTP_USER = "technicellreparaciones@gmail.com"      # tu usuario SMTP (email)
SMTP_PASSWORD = "pgpk ydyj fgfp njut"          # <-- CAMBIALO por tu app password (NO subir a git)
SMTP_FROM = "Technicell <technicellreparaciones@gmail.com>"  # valor visible en From
SMTP_USE_SSL = True                             # True -> SMTP_SSL (puerto 465). False -> STARTTLS (puerto 587)

# ============================
# === OVERRIDE POR ENV VARS ==
# ============================
# Si quieres mantener variables en este archivo pero permitir override por env vars
# (útil para staging/producción), descomenta las líneas siguientes o déjalas activas:
SMTP_HOST = os.environ.get("SMTP_HOST", SMTP_HOST)
SMTP_PORT = int(os.environ.get("SMTP_PORT", SMTP_PORT))
SMTP_USER = os.environ.get("SMTP_USER", SMTP_USER)
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", SMTP_PASSWORD)
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_FROM)
SMTP_USE_SSL = str(os.environ.get("SMTP_USE_SSL", str(int(SMTP_USE_SSL)))).lower() in ("1", "true", "yes")

# ============================
# === FUNCIONES PRINCIPALES ==
# ============================
def _safe_escape(text: Optional[str]) -> str:
    return escape(text or "")


def enviar_email_reparacion(
    to_email: str,
    cliente_nombre: str,
    ticket_id: str,
    modelo: str,
    falla: str,
    message_from_front: Optional[str] = None,
    timeout: int = 30,
) -> None:
    """
    Envía un correo HTML notificando que el equipo entró a reparación.
    Lanza RuntimeError en caso de fallo para que el router capture y devuelva HTTP 500.

    Parámetros:
      - to_email: destinatario
      - cliente_nombre, ticket_id, modelo, falla: datos para el cuerpo
      - message_from_front: mensaje opcional desde el frontend
      - timeout: segundos de timeout para conexión SMTP
    """

    # Sanitizar entradas
    cliente_nombre_safe = _safe_escape(cliente_nombre or "Cliente")
    ticket_id_safe = _safe_escape(str(ticket_id))
    modelo_safe = _safe_escape(modelo or "")
    falla_safe = _safe_escape(falla or "")
    mensaje_custom = _safe_escape(message_from_front or "")

    # Construir body HTML y text
    mensaje_html = ""
    if mensaje_custom:
        mensaje_html = (
            "<div style='margin-top:12px'>"
            "<div class='label'>Mensaje:</div>"
            f"<div class='value' style='font-weight:500;color:#333'>{mensaje_custom}</div>"
            "</div>"
        )

    subject = "Technicell — Su equipo ha entrado en reparación"

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

    # Construir mensaje MIME
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")

    # Intentar enviar y propagar excepciones si hay fallo
    try:
        if SMTP_USE_SSL:
            logger.debug("Envío de correo: usando SMTP_SSL (%s:%s)", SMTP_HOST, SMTP_PORT)
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=timeout) as server:
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            logger.debug("Envío de correo: usando STARTTLS (%s:%s)", SMTP_HOST, SMTP_PORT)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=timeout) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

        logger.info("Correo enviado a %s (ticket %s)", to_email, ticket_id)
    except Exception as exc:
        # Loggear con stacktrace para debug y luego lanzar error controlado
        logger.exception("Error al enviar correo via SMTP: %s", exc)
        # Lanzar RuntimeError para que el router lo convierta a HTTPException y lo veas en Postman
        raise RuntimeError(f"Error al enviar el correo: {exc}") from exc


# ============================
# === Helper de prueba ===
# ============================
def test_send():
    """Función de prueba local. Ejecutar solo en entorno de desarrollo."""
    try:
        enviar_email_reparacion(
            to_email=os.environ.get("TEST_EMAIL", "tu_correo_de_prueba@ejemplo.com"),
            cliente_nombre="Prueba",
            ticket_id="TEST-123",
            modelo="iPhone X",
            falla="Test de envío",
            message_from_front="Mensaje de prueba desde test_send()"
        )
        print("Envío de prueba: OK")
    except Exception as e:
        print("Envío de prueba: FALLÓ ->", e)


if __name__ == "__main__":
    # Ejecutar test rápido si corres este file directamente (local only)
    test_send()
