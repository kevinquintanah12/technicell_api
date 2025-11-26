# utils/tickets_reparacion.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)

# Reusar A5 si lo tienes definido en utils/tickets.py; si no, definimos A5 simple:
A5 = (148 * mm, 210 * mm)


def _get_tickets_dir(path: Optional[str] = "tickets") -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / path).resolve()
    tickets_dir.mkdir(parents=True, exist_ok=True)
    return tickets_dir


def _draw_header_simple(c: canvas.Canvas, ancho: float, alto: float, margin: float, logo_full: Path, company: str, subtitle: str) -> float:
    """
    Header simple: logo centrado y textos. Devuelve y inicial del contenido.
    Si ya tienes _draw_header en utils/tickets.py puedes reemplazar llamando a esa función.
    """
    y = alto - margin
    max_logo_h = 25 * mm
    max_logo_w = ancho - 2 * margin
    logo_present = logo_full.exists()
    if logo_present:
        try:
            from PIL import Image
            with Image.open(str(logo_full)) as im:
                img_w_px, img_h_px = im.size
                ratio = img_w_px / img_h_px if img_h_px != 0 else 1.0
                logo_h = min(max_logo_h, max_logo_w / ratio)
                logo_w = logo_h * ratio
        except Exception:
            logo_w = min(max_logo_w, 50 * mm)
            logo_h = min(max_logo_h, 50 * mm)
        logo_x = (ancho - logo_w) / 2
        logo_y = y - logo_h
        try:
            c.drawImage(str(logo_full), x=logo_x, y=logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, anchor="c", mask='auto')
        except Exception:
            try:
                c.drawImage(str(logo_full), x=logo_x, y=logo_y, width=logo_w, height=logo_h, mask='auto')
            except Exception:
                logger.exception("No se pudo dibujar logo en ticket_reparacion header")
        y = logo_y - (3 * mm)
    else:
        y -= 6 * mm

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(ancho / 2, y, company)
    y -= 5 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(ancho / 2, y, subtitle)
    y -= 6 * mm
    c.setLineWidth(0.5)
    c.line(margin, y, ancho - margin, y)
    y -= 6 * mm
    return y


def generar_ticket_ingreso_reparacion(
    cliente_nombre: str,
    contacto: Optional[str],
    articulo: str,
    modelo: Optional[str] = None,
    serie: Optional[str] = None,
    falla_descripcion: Optional[str] = None,
    observaciones: Optional[str] = None,
    tipo_ticket: str = "Físico",  # "Físico" o "Electrónico"
    fecha_ingreso: Optional[datetime] = None,
    plazo_estimado: Optional[str] = None,
    path: str = "tickets",
    logo_path: str = "static/logogo.png",
    company_name: str = "TECHNICELL",
) -> str:
    """
    Genera un ticket PDF de ingreso/recepción para reparación.
    - tipo_ticket: 'Físico' o 'Electrónico'
    - incluye la cláusula de garantía para ticket electrónico
    Devuelve la ruta absoluta del PDF generado.
    """
    fecha_ingreso = fecha_ingreso or datetime.now()
    tickets_dir = _get_tickets_dir(path)
    timestamp = fecha_ingreso.strftime("%Y%m%d_%H%M%S")
    nombre_archivo = tickets_dir / f"ticket_ingreso_reparacion_{timestamp}.pdf"

    ancho, alto = A5
    margin = 10 * mm
    left_x = margin
    right_x = ancho - margin
    line_h = 6.0 * mm

    logo_full = Path(__file__).resolve().parent.parent / logo_path

    try:
        c = canvas.Canvas(str(nombre_archivo), pagesize=A5)
        subtitle = "Recibo de ingreso / Recepción de equipo"
        y = _draw_header_simple(c, ancho, alto, margin, logo_full, company_name, subtitle)

        # Datos del cliente / dispositivo
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Cliente:")
        c.setFont("Helvetica", 9)
        c.drawString(left_x + 28 * mm, y, f"{cliente_nombre}")
        y -= line_h

        if contacto:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Contacto:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, contacto)
            y -= line_h

        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Artículo:")
        c.setFont("Helvetica", 9)
        c.drawString(left_x + 28 * mm, y, articulo)
        y -= line_h

        if modelo:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Modelo:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, modelo)
            y -= line_h

        if serie:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Serie / IMEI:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, serie)
            y -= line_h

        # Falla / descripcion
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Falla reportada:")
        y -= (line_h - 2 * mm)
        c.setFont("Helvetica", 9)
        # wrap simple: si la línea es larga, saltar manualmente
        text = c.beginText(left_x, y)
        text.setFont("Helvetica", 9)
        max_w = (ancho - 2 * margin)
        for ln in _wrap_text(str(falla_descripcion or "No especificada"), 48):
            text.textLine(ln)
            y -= (4.5 * mm)
        c.drawText(text)
        y -= (2 * mm)

        # Observaciones
        if observaciones:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Observaciones:")
            y -= (line_h - 2 * mm)
            c.setFont("Helvetica", 9)
            text_obs = c.beginText(left_x, y)
            text_obs.setFont("Helvetica", 9)
            for ln in _wrap_text(observaciones, 50):
                text_obs.textLine(ln)
                y -= (4.5 * mm)
            c.drawText(text_obs)
            y -= (2 * mm)

        # Fecha / tipo de ticket / plazo estimado
        y -= (2 * mm)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Fecha ingreso:")
        c.setFont("Helvetica", 9)
        c.drawString(left_x + 28 * mm, y, fecha_ingreso.strftime("%d/%m/%Y %H:%M"))
        y -= line_h

        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Tipo de ticket:")
        c.setFont("Helvetica", 9)
        c.drawString(left_x + 28 * mm, y, tipo_ticket)
        y -= line_h

        if plazo_estimado:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Plazo estimado:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, plazo_estimado)
            y -= line_h

        y -= (4 * mm)

        # Línea separadora
        c.setLineWidth(0.4)
        c.line(left_x, y, right_x, y)
        y -= (6 * mm)

        # Aviso / cláusula que pediste
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(ancho / 2, y, "IMPORTANTE")
        y -= (5 * mm)
        c.setFont("Helvetica", 8)
        aviso_lines = [
            "El artículo se entregará junto con el ticket físico o electrónico.",
            "Sin embargo, el ticket electrónico NO tiene garantía. Conserva tu ticket.",
            "El tiempo de reparación será tomado en consideración al momento de resolver la incidencia.",
        ]
        for ln in aviso_lines:
            # centrar y permitir wrap simple
            for sub in _wrap_text(ln, 60):
                c.drawCentredString(ancho / 2, y, sub)
                y -= (4.5 * mm)
        y -= (4 * mm)

        # Espacio firma / recepción
        c.setFont("Helvetica", 9)
        c.drawString(left_x, y, "Recibido por (firma): ____________________________")
        y -= (10 * mm)
        c.drawString(left_x, y, "Entrega prevista (firma cliente): __________________")
        y -= (10 * mm)

        # Pie: datos contacto o agradecimiento
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(ancho / 2, margin + (6 * mm), f"{company_name} - Servicio técnico")
        y -= (4 * mm)

        # finaliza
        c.showPage()
        c.save()
    except Exception as e:
        logger.exception("Error generando ticket de ingreso/reparacion")
        try:
            if nombre_archivo.exists() and nombre_archivo.stat().st_size == 0:
                nombre_archivo.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"Error generando ticket ingreso reparacion: {e}")

    # Verificación
    if not nombre_archivo.exists() or nombre_archivo.stat().st_size == 0:
        raise RuntimeError("No se pudo generar el ticket de ingreso (archivo vacío o inexistente)")

    logger.debug("Ticket ingreso generado: %s", nombre_archivo)
    return str(nombre_archivo)


def _wrap_text(text: str, max_chars: int):
    """
    Helper muy simple para dividir texto en líneas con max_chars caracteres.
    Para layouts más robustos usa reportlab.platypus. Aquí sirve para A5.
    """
    if not text:
        return [""]
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        if len(cur) + 1 + len(w) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
