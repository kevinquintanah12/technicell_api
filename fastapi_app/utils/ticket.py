# utils/tickets_reparacion.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import os
from utils.ticket_counter import obtener_siguiente_numero_ticket

logger = logging.getLogger(__name__)

# A5 (horizontal/vertical) para tickets pequeños
A5 = (148 * mm, 210 * mm)


def _get_tickets_dir(path: Optional[str] = "tickets") -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / path).resolve()
    tickets_dir.mkdir(parents=True, exist_ok=True)
    return tickets_dir


def _draw_header_simple(
    c: canvas.Canvas,
    ancho: float,
    alto: float,
    margin: float,
    logo_full: Path,
    company: str,
    subtitle: str,
) -> float:
    """
    Header simple: logo centrado y textos. Devuelve la Y inicial del contenido.
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
            c.drawImage(
                str(logo_full),
                x=logo_x,
                y=logo_y,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                anchor="c",
                mask="auto",
            )
        except Exception:
            try:
                c.drawImage(str(logo_full), x=logo_x, y=logo_y, width=logo_w, height=logo_h, mask="auto")
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
    cliente_nombre: Optional[str] = None,
    contacto: Optional[str] = None,
    articulo: Optional[str] = None,
    modelo: Optional[str] = None,
    serie: Optional[str] = None,
    falla_descripcion: Optional[str] = None,
    observaciones: Optional[str] = None,
    # campos de cobro/opcionales
    anticipo: Optional[float] = 0.0,
    total: Optional[float] = 0.0,
    tipo_pago: Optional[str] = None,
    monto_recibido: Optional[float] = 0.0,
    cambio: Optional[float] = 0.0,
    tipo_ticket: str = "Físico",  # "Físico" o "Electrónico"
    fecha_ingreso: Optional[datetime] = None,
    plazo_estimado: Optional[str] = None,
    path: str = "tickets",
    logo_path: str = "static/logogo.png",
    company_name: str = "TECHNICELL",
    # Soporta recibir todo el ingreso como dict (por compatibilidad con llamadas antiguas)
    ingreso: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Genera un ticket PDF de ingreso/recepción para reparación.
    Acepta dos formas:
      - pasar los parámetros individuales (cliente_nombre, articulo, etc.)
      - pasar `ingreso` (dict) con keys compatibles:
            cliente_nombre, contacto/telefono, articulo/equipo, modelo, serie/imei,
            falla_descripcion/falla, observaciones, anticipo, total, tipo_pago, monto_recibido
    Devuelve la ruta absoluta del PDF generado.
    """
    # Si se envió `ingreso` como dict, sobreescribimos valores con lo que venga ahí.
    if ingreso and isinstance(ingreso, dict):
        # mapping flexible: acepta varios nombres comunes
        cliente_nombre = cliente_nombre or ingreso.get("cliente_nombre") or ingreso.get("nombre_cliente") or ingreso.get("cliente")
        contacto = contacto or ingreso.get("telefono") or ingreso.get("contacto")
        articulo = articulo or ingreso.get("articulo") or ingreso.get("equipo") or ingreso.get("marca")
        modelo = modelo or ingreso.get("modelo")
        serie = serie or ingreso.get("imei") or ingreso.get("serie")
        falla_descripcion = falla_descripcion or ingreso.get("falla") or ingreso.get("falla_reportada") or ingreso.get("problema")
        observaciones = observaciones or ingreso.get("observaciones")
        # cobro
        anticipo = anticipo if anticipo not in (None,) else ingreso.get("anticipo", 0.0)
        total = total if total not in (None,) else ingreso.get("total_estimado", ingreso.get("total", 0.0))
        tipo_pago = tipo_pago or ingreso.get("tipo_pago")
        monto_recibido = monto_recibido if monto_recibido not in (None,) else ingreso.get("monto_recibido", 0.0)
        cambio = cambio if cambio not in (None,) else ingreso.get("cambio", 0.0)
        fecha_ingreso = fecha_ingreso or ingreso.get("fecha_ingreso")

    # Valores por defecto mínimos
    fecha_ingreso = fecha_ingreso or datetime.now()
    cliente_nombre = cliente_nombre or "Cliente"
    articulo = articulo or "Artículo"
    falla_descripcion = falla_descripcion or "No especificada"

    
    tickets_dir = _get_tickets_dir(path)

# obtener número del ticket (1..100)
    numero_ticket = obtener_siguiente_numero_ticket(tickets_dir)

# nombre del archivo usando la numeración rotativa
    nombre_archivo = tickets_dir / f"ticket_ingreso_reparacion_{numero_ticket}.pdf"

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

        # Cliente / dispositivo
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Cliente:")
        c.setFont("Helvetica", 9)
        c.drawString(left_x + 28 * mm, y, f"{cliente_nombre}")
        y -= line_h

        if contacto:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Contacto:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, f"{contacto}")
            y -= line_h

        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Artículo:")
        c.setFont("Helvetica", 9)
        c.drawString(left_x + 28 * mm, y, f"{articulo}")
        y -= line_h

        if modelo:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Modelo:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, f"{modelo}")
            y -= line_h

        if serie:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Serie / IMEI:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, f"{serie}")
            y -= line_h

        # Falla / descripcion (wrap simple)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Falla reportada:")
        y -= (line_h - 2 * mm)
        c.setFont("Helvetica", 9)
        text = c.beginText(left_x, y)
        text.setFont("Helvetica", 9)
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

        # Espacio antes de sección cobro/fecha
        y -= (2 * mm)

        # Cobro (si se pasaron datos de cobro, los mostramos)
        show_cobro = any(x not in (None, 0, 0.0, "") for x in (anticipo, total, tipo_pago, monto_recibido, cambio))
        if show_cobro:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "Cobro:")
            y -= (line_h - 2 * mm)
            c.setFont("Helvetica", 9)
            if total not in (None, 0, 0.0):
                c.drawString(left_x + 6 * mm, y, f"Total estimado: ${float(total):.2f}")
                y -= (line_h - 2 * mm)
            if anticipo not in (None, 0, 0.0):
                c.drawString(left_x + 6 * mm, y, f"Anticipo cobrado: ${float(anticipo):.2f}")
                y -= (line_h - 2 * mm)
            if tipo_pago:
                c.drawString(left_x + 6 * mm, y, f"Tipo de pago: {tipo_pago}")
                y -= (line_h - 2 * mm)
            if monto_recibido not in (None, 0, 0.0):
                c.drawString(left_x + 6 * mm, y, f"Monto recibido: ${float(monto_recibido):.2f}")
                y -= (line_h - 2 * mm)
            if cambio not in (None, 0, 0.0):
                c.drawString(left_x + 6 * mm, y, f"Cambio: ${float(cambio):.2f}")
                y -= (line_h - 2 * mm)

            # pequeña separación
            y -= (2 * mm)

        # Fecha / tipo de ticket / plazo estimado
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

        # Aviso / cláusula
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

        # Pie
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(ancho / 2, margin + (6 * mm), f"{company_name} - Servicio técnico")

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
