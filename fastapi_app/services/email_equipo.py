import smtplib
from typing import Optional
from email.mime.text import MIMEText
from html import escape

# =========================
# CONFIG SMTP (HARDCODED)
# =========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "technicellorizaba@gmail.com"
SMTP_PASS = "wvdh hbwt vdin ijxj"  # ⚠️ solo dev

LOGO_URL = "https://i.imgur.com/4X0QZ2q.png"
SUPPORT_PHONE = "+522711764587"
SUPPORT_EMAIL = "technicellorizaba@gmail.com"
FOLLOW_BASE_URL = "https://www.technicell.com"


def enviar_email_reparacion(
    to_email: str,
    cliente_nombre: str,
    ticket_id: str,
    modelo: str,
    falla: str,
    message_from_front: Optional[str] = None,
):
    """
    Envía el email HTML de notificación de 'EN REPARACIÓN'
    (configuración idéntica al módulo GraphQL)
    """

    # =========================
    # SANITIZAR
    # =========================
    cliente_nombre_safe = escape(cliente_nombre or "Cliente")
    ticket_id_safe = escape(str(ticket_id))
    modelo_safe = escape(modelo or "")
    falla_safe = escape(falla or "")
    mensaje_custom = escape(message_from_front or "")

    if mensaje_custom:
        mensaje_html = (
            "<div style='margin-top:12px'>"
            "<div class='label'>Mensaje:</div>"
            f"<div class='value' style='font-weight:500;color:#333'>{mensaje_custom}</div>"
            "</div>"
        )
    else:
        mensaje_html = ""

    subject = "Technicell — Su equipo ha entrado en reparación"

    # =========================
    # HTML TEMPLATE
    # =========================
    body_template = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Technicell</title>
</head>
<body style="background:#f4f4f6;padding:20px;font-family:Arial">
  <div style="max-width:680px;margin:auto;background:#fff;border-radius:8px;padding:20px">
    <h2 style="color:#6b46c1">Hola @@CLIENTE_NOMBRE@@ 👋</h2>

    <p>Su equipo <strong>@@MODELO@@</strong> ha cambiado al estado:</p>

    <h3 style="color:#fff;background:#6b46c1;display:inline-block;padding:8px 14px;border-radius:20px">
      EN REPARACIÓN
    </h3>

    <hr style="margin:20px 0">

    <p><strong>Ticket:</strong> #@@TICKET_ID@@</p>
    <p><strong>Falla reportada:</strong><br>@@FALLA@@</p>

    @@MENSAJE_CUSTOM_HTML@@

    <p style="margin-top:20px">
      Gracias por su preferencia.<br>
      <strong>Technicell</strong><br>
      Pte. 7 269, Centro, Orizaba
    </p>

    <p style="font-size:13px;color:#666">
      Soporte: @@SUPPORT_PHONE@@ · @@SUPPORT_EMAIL@@
    </p>
  </div>
</body>
</html>
"""

    body = (
        body_template
        .replace("@@CLIENTE_NOMBRE@@", cliente_nombre_safe)
        .replace("@@TICKET_ID@@", ticket_id_safe)
        .replace("@@MODELO@@", modelo_safe)
        .replace("@@FALLA@@", falla_safe)
        .replace("@@MENSAJE_CUSTOM_HTML@@", mensaje_html)
        .replace("@@SUPPORT_PHONE@@", SUPPORT_PHONE)
        .replace("@@SUPPORT_EMAIL@@", SUPPORT_EMAIL)
    )

    # =========================
    # ENVIAR EMAIL (MISMO QUE GRAPHQL)
    # =========================
    message = MIMEText(body, "html")
    message["Subject"] = subject
    message["From"] = SMTP_USER
    message["To"] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], message.as_string())
    except Exception as e:
        print(f"Error al enviar email de reparación: {e}")
        raise
