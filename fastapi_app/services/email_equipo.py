import smtplib
from typing import Optional
from email.mime.text import MIMEText
from html import escape


def enviar_email_reparacion(
    to_email: str,
    cliente_nombre: str,
    ticket_id: str,
    modelo: str,
    falla: str,
    message_from_front: Optional[str] = None,
):
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
    # HTML
    # =========================
    body = f"""<!doctype html>
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

    # =========================
    # ENVÍO SIMPLE (IGUAL A GRAPHQL)
    # =========================
    sender_email = "technicellorizaba@gmail.com"
    app_password = "wvdh hbwt vdin ijxj"

    message = MIMEText(body, "html")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, [to_email], message.as_string())
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
