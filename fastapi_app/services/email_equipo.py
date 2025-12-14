# services/email_equipo.py
import os
import smtplib
from typing import Optional
from email.mime.text import MIMEText
from html import escape

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 465))
SMTP_USER = os.environ.get("SMTP_USER", "technicellorizaba@gmail.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "wvdh hbwt vdin ijxj")  # reemplaza en prod

LOGO_URL = "https://i.imgur.com/4X0QZ2q.png"
SUPPORT_PHONE = "+522711764587"
SUPPORT_EMAIL = "technicellorizaba@gmail.com"
FOLLOW_BASE_URL = os.environ.get("APP_BASE_URL", "https://www.technicell.com")


def enviar_email_reparacion(
    to_email: str,
    cliente_nombre: str,
    ticket_id: str,
    modelo: str,
    falla: str,
    message_from_front: Optional[str] = None,
):
    """
    Envía el email HTML de notificación de 'EN REPARACIÓN'.
    Se usa Optional[str] para compatibilidad con Python < 3.10.
    """
    # Sanitizar/escapar entradas
    cliente_nombre_safe = escape(cliente_nombre or "Cliente")
    ticket_id_safe = escape(str(ticket_id))
    modelo_safe = escape(modelo or "")
    falla_safe = escape(falla or "")
    mensaje_custom = escape(message_from_front or "")

    # html para el mensaje personalizado (si viene)
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

    # Plantilla con marcadores únicos (sin usar f-strings)
    body_template = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Notificación de estado - Technicell</title>
  <style>
    body,table,td{margin:0;padding:0;border:0;font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;}
    img{border:0;display:block;max-width:100%;height:auto}
    a{color:inherit;text-decoration:none}
    .email-wrap{width:100%;background:#f4f4f6;padding:30px 16px}
    .email-container{max-width:700px;margin:0 auto;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 6px 18px rgba(15,15,20,0.06)}
    .header{background:linear-gradient(90deg, #ffb300 0%, #ffca28 100%);padding:18px 24px;color:#111;display:flex;align-items:center;justify-content:space-between}
    .brand{display:flex;align-items:center;gap:12px}
    .brand img{width:48px;height:48px;border-radius:6px;object-fit:cover}
    .brand h1{font-size:18px;margin:0;color:#111}
    .hero{padding:26px 24px;border-bottom:1px solid #eee}
    .status-badge{display:inline-block;padding:8px 12px;border-radius:20px;font-weight:700;font-size:13px;color:#fff;background:#6b46c1}
    .title{font-size:20px;margin:12px 0 6px;color:#111}
    .lead{color:#555;line-height:1.45;margin:0}
    .card{background:#fafafa;border:1px solid #f0f0f2;border-radius:8px;padding:16px;margin-top:16px}
    .row{display:flex;gap:12px;flex-wrap:wrap}
    .col{flex:1 1 200px;min-width:160px}
    .label{font-size:12px;color:#8a8a9a;margin-bottom:6px}
    .value{font-size:15px;color:#111;font-weight:600}
    .cta{display:inline-block;margin-top:18px;padding:12px 18px;border-radius:8px;background:#111827;color:#fff;font-weight:700}
    .secondary{display:inline-block;margin-top:12px;margin-left:10px;padding:10px 14px;border-radius:8px;border:1px solid #ddd;background:#fff;color:#111}
    .footer{padding:18px 24px;font-size:13px;color:#6b6b75;background:#f8f9fb;border-top:1px solid #eee}
    .address{color:#3b3b45;font-weight:600}
    .small{font-size:12px;color:#8a8a9a}
    @media (max-width:520px){ .header{padding:14px} .hero{padding:18px} .email-wrap{padding:18px 10px} .brand h1{font-size:16px} }
  </style>
</head>
<body>
  <div class="email-wrap">
    <div class="email-container" role="article" aria-roledescription="email">

      <!-- Header -->
      <div class="header">
        <div class="brand">
          <img src="@@LOGO_URL@@" alt="Technicell logo" />
          <div>
            <h1>Technicell</h1>
            <div style="font-size:12px;color:#222;">Servicio técnico | Plaza Bicentenario, Orizaba</div>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:12px;color:#111;">Soporte: <a href="tel:@@SUPPORT_PHONE@@">@@SUPPORT_PHONE@@</a></div>
          <div style="font-size:12px;color:#111;margin-top:6px">Horario: Lun–Sáb 10:00–19:00</div>
        </div>
      </div>

      <!-- Hero / Estado -->
      <div class="hero">
        <span class="status-badge">EN REPARACIÓN</span>
        <h2 class="title">Hola @@CLIENTE_NOMBRE@@, su equipo <span style="color:#6b46c1">(@@MODELO@@)</span> ha pasado a estado:</h2>
        <p class="lead">Le notificamos que su equipo fue recibido por nuestro personal y actualmente se encuentra en proceso de diagnóstico y reparación. Se le avisará por este medio cuando pueda recoger su equipo.</p>

        <!-- Tarjeta de detalles -->
        <div class="card" role="region" aria-label="Detalles del equipo">
          <div class="row">
            <div class="col">
              <div class="label">Ticket / ID</div>
              <div class="value">#<strong>@@TICKET_ID@@</strong></div>
            </div>
            <div class="col">
              <div class="label">Equipo</div>
              <div class="value">@@MODELO@@</div>
            </div>
            <div class="col">
              <div class="label">Estado actual</div>
              <div class="value">EN REPARACIÓN</div>
            </div>
          </div>

          <div style="margin-top:12px">
            <div class="label">Falla reportada</div>
            <div class="value" style="font-weight:500;color:#333">@@FALLA@@</div>
          </div>

          <!-- Mensaje personalizado desde front -->
          @@MENSAJE_CUSTOM_HTML@@

          <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
            <a class="cta" href="@@FOLLOW_BASE_URL@@/seguimiento/@@TICKET_ID@@" target="_blank" rel="noopener">Ver estado del equipo</a>
            <a class="secondary" href="mailto:@@SUPPORT_EMAIL@@?subject=Consulta%20Ticket%20@@TICKET_ID@@" target="_blank">Contactar soporte</a>
          </div>
        </div>

        <p class="small" style="margin-top:14px">Nuestro equipo estimará el tiempo y el costo de la reparación tras completar el diagnóstico. Si necesita autorización previa para cualquier reparación mayor, nos comunicaremos por teléfono o correo.</p>
      </div>

      <!-- Footer -->
      <div class="footer">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
          <div>
            <div class="address">Technicell — Pte. 7 269, Centro, 94300 Orizaba, Ver.</div>
            <div class="small" style="margin-top:6px">Plaza Bicentenario · <a href="https://maps.app.goo.gl/mXJT2TiTh34NPEJ29" target="_blank">Abrir mapa</a></div>
          </div>
          <div style="text-align:right">
            <div class="small">¿Necesita ayuda? <a href="mailto:@@SUPPORT_EMAIL@@">@@SUPPORT_EMAIL@@</a></div>
            <div style="margin-top:8px" class="small">Síganos: <a href="https://www.facebook.com/technicell" target="_blank">Facebook</a> · <a href="https://www.instagram.com/technicell" target="_blank">Instagram</a></div>
          </div>
        </div>

        <div style="margin-top:12px;border-top:1px solid #eee;padding-top:12px;text-align:center;font-size:12px;color:#9a9aa2">
          Este correo es informativo. Si desea darse de baja de notificaciones automáticas <a href="@@FOLLOW_BASE_URL@@/unsubscribe">haga clic aquí</a>.
        </div>
      </div>

    </div>
  </div>
</body>
</html>
"""

    # Reemplazar marcadores por valores seguros
    body = (
        body_template
        .replace("@@LOGO_URL@@", LOGO_URL)
        .replace("@@SUPPORT_PHONE@@", SUPPORT_PHONE)
        .replace("@@SUPPORT_EMAIL@@", SUPPORT_EMAIL)
        .replace("@@FOLLOW_BASE_URL@@", FOLLOW_BASE_URL)
        .replace("@@CLIENTE_NOMBRE@@", cliente_nombre_safe)
        .replace("@@TICKET_ID@@", ticket_id_safe)
        .replace("@@MODELO@@", modelo_safe)
        .replace("@@FALLA@@", falla_safe)
        .replace("@@MENSAJE_CUSTOM_HTML@@", mensaje_html)
    )

    # Construir y enviar
    message = MIMEText(body, "html")
    message["Subject"] = subject
    message["From"] = SMTP_USER
    message["To"] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], message.as_string())
    except Exception:
        # Dejar que el llamador maneje la excepción (o registra aquí)
        raise
