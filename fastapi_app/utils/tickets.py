# utils/tickets.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)

# A5 manual (ReportLab no siempre expone A5)
A5 = (148 * mm, 210 * mm)


def _to_detalle_dict(d: Any) -> Dict[str, Any]:
    detalle = {"producto": None, "cantidad": 1, "precio_unitario": 0.0, "subtotal": None}

    if isinstance(d, dict):
        detalle["producto"] = d.get("producto") or d.get("producto_nombre") or (
            d.get("producto") and (d.get("producto").get("nombre") if isinstance(d.get("producto"), dict) else None)
        )
        detalle["cantidad"] = d.get("cantidad", detalle["cantidad"])
        detalle["precio_unitario"] = d.get("precio_unitario") or d.get("precio") or d.get("precio_venta") or 0.0
        detalle["subtotal"] = d.get("subtotal")
        return detalle

    try:
        prod = getattr(d, "producto", None)
        if prod is not None:
            nombre_prod = getattr(prod, "nombre", None) if not isinstance(prod, str) else prod
            detalle["producto"] = nombre_prod or str(prod)
        else:
            detalle["producto"] = getattr(d, "producto_nombre", None) or getattr(d, "nombre", None)
    except Exception:
        detalle["producto"] = None

    try:
        detalle["cantidad"] = getattr(d, "cantidad", detalle["cantidad"])
    except Exception:
        detalle["cantidad"] = detalle["cantidad"]

    try:
        detalle["precio_unitario"] = getattr(d, "precio_unitario", None) or getattr(d, "precio", None) or getattr(d, "precio_venta", 0.0)
    except Exception:
        detalle["precio_unitario"] = 0.0

    try:
        detalle["subtotal"] = getattr(d, "subtotal", None)
    except Exception:
        detalle["subtotal"] = None

    return detalle


def _safe_float(val: Optional[Any], default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def _get_tickets_dir(path: Optional[str] = "tickets") -> Path:
    """
    Devuelve la carpeta absoluta donde guardar los tickets.
    """
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / path).resolve()
    tickets_dir.mkdir(parents=True, exist_ok=True)
    return tickets_dir


def _fit_text(canvas_obj, text: str, max_width: float, fontname: str, fontsize: float) -> str:
    """
    Devuelve una versión truncada con '...' si el texto supera max_width.
    Usa canvas_obj.stringWidth para medir.
    """
    if not text:
        return ""
    width = canvas_obj.stringWidth(text, fontname, fontsize)
    if width <= max_width:
        return text
    ellipsis = "..."
    ellipsis_w = canvas_obj.stringWidth(ellipsis, fontname, fontsize)
    # Binary-ish truncation
    low, high = 0, len(text)
    while low < high:
        mid = (low + high) // 2
        candidate = text[:mid].rstrip()
        if canvas_obj.stringWidth(candidate, fontname, fontsize) + ellipsis_w <= max_width:
            low = mid + 1
        else:
            high = mid
    safe_text = text[:max(0, low - 1)].rstrip()
    return safe_text + ellipsis


def _draw_header(c: canvas.Canvas, ancho: float, alto: float, margin: float, logo_full: Path, company: str, subtitle: str):
    """
    Dibuja encabezado con logo centrado y textos centrados debajo.
    Devuelve la y de inicio del contenido (punto desde donde comienza a listar productos).
    """
    y = alto - margin

    # Logo: intentaremos un size relativo (máx 30 mm de alto)
    max_logo_h = 30 * mm
    max_logo_w = ancho - 2 * margin
    logo_present = logo_full.exists()
    if logo_present:
        try:
            # intentamos mantener aspect ratio; usamos reportlab to get image size via PIL if available
            from PIL import Image
            with Image.open(str(logo_full)) as im:
                img_w_px, img_h_px = im.size
                # ratio in points (pixels -> points is handled roughly by keeping aspect ratio)
                # compute scale to fit max dimensions
                ratio = img_w_px / img_h_px if img_h_px != 0 else 1.0
                logo_h = min(max_logo_h, max_logo_w / ratio)
                logo_w = logo_h * ratio
        except Exception:
            # fallback sizes if PIL no disponible
            logo_w = min(max_logo_w, 50 * mm)
            logo_h = min(max_logo_h, 50 * mm)
        logo_x = (ancho - logo_w) / 2
        logo_y = y - logo_h
        try:
            c.drawImage(str(logo_full), x=logo_x, y=logo_y, width=logo_w, height=logo_h, preserveAspectRatio=True, anchor="c", mask='auto')
        except Exception:
            # fallback: intentar dibujar sin preserveAspectRatio
            try:
                c.drawImage(str(logo_full), x=logo_x, y=logo_y, width=logo_w, height=logo_h, mask='auto')
            except Exception:
                logger.exception("No se pudo dibujar el logo en el ticket (header)")

        y = logo_y - (4 * mm)  # espacio después del logo
    else:
        # si no hay logo, dejar espacio pequeño
        y -= 6 * mm

    # Empresa y subtítulo centrados
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(ancho / 2, y, company)
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(ancho / 2, y, subtitle)
    y -= 6 * mm

    # Línea separadora
    c.setLineWidth(0.5)
    c.line(margin, y, ancho - margin, y)
    y -= 6 * mm

    return y


def generar_ticket_venta_multiple(
    detalles: List[Any],
    total: float,
    tipo_pago: str,
    monto_recibido: float,
    cambio: float,
    path: str = "tickets",
    logo_path: str = "static/logogo.png"
) -> str:
    """
    Genera un ticket PDF para una venta con varios detalles.
    Devuelve la ruta absoluta del PDF generado.
    Lanza RuntimeError si algo sale mal o el archivo no existe / está vacío.
    """
    tickets_dir = _get_tickets_dir(path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = tickets_dir / f"ticket_venta_{timestamp}.pdf"

    # Normalizar si recibieron dict con "detalles"
    if isinstance(detalles, dict) and "detalles" in detalles:
        detalles_list = detalles.get("detalles", [])
    else:
        detalles_list = detalles or []

    ancho, alto = A5

    # medidas y márgenes en mm convertidos a puntos (reportlab ya usa puntos)
    margin = 10 * mm
    line_height = 5.5 * mm
    font_main = "Helvetica"
    font_bold = "Helvetica-Bold"

    logo_full = Path(__file__).resolve().parent.parent / logo_path

    try:
        c = canvas.Canvas(str(nombre_archivo), pagesize=A5)

        # dibujar header (logo + company)
        company_name = "TECHNICELL"
        subtitle = "Recibo de venta"
        y = _draw_header(c, ancho, alto, margin, logo_full, company_name, subtitle)

        # titulos de columnas
        c.setFont(font_bold, 9)
        left_x = margin
        right_x = ancho - margin
        # Reserve column for qty and price if needed
        qty_col_w = 18 * mm
        price_col_w = 30 * mm
        name_col_w = (ancho - 2 * margin) - qty_col_w - price_col_w - (6 * mm)  # espacio entre columnas

        # Dibujar cabecera de tabla de productos
        c.drawString(left_x, y, "Productos")
        y -= line_height
        c.setFont(font_main, 9)

        # iterar productos
        for raw in detalles_list:
            d = _to_detalle_dict(raw)
            cantidad = int(d.get("cantidad") or 1)
            precio_unit = _safe_float(d.get("precio_unitario"))
            subtotal = d.get("subtotal")
            if subtotal is None:
                subtotal = cantidad * precio_unit
            subtotal = _safe_float(subtotal)
            producto_nombre = (d.get("producto") or d.get("producto_nombre") or "Producto")

            # Si no cabe, truncar nombre con _fit_text
            max_name_w = name_col_w
            display_name = _fit_text(c, producto_nombre, max_name_w, font_main, 9)

            # posición columnas
            name_x = left_x
            qty_x = left_x + name_col_w + (3 * mm)
            price_x = qty_x + qty_col_w + (3 * mm)
            # Imprimir nombre
            c.drawString(name_x, y, display_name)
            # Imprimir cantidad (centrado en su columna aproximada)
            c.drawCentredString(qty_x + (qty_col_w / 2), y, str(cantidad))
            # Imprimir subtotal a la derecha
            c.drawRightString(right_x, y, f"${subtotal:.2f}")
            y -= line_height

            # salto de página si hace falta
            if y < margin + 40:  # dejar espacio para footer
                c.showPage()
                # nuevo header en nueva página
                y = _draw_header(c, ancho, alto, margin, logo_full, company_name, subtitle)
                c.setFont(font_main, 9)

        # espacio antes de totales
        y -= (4 * mm)
        c.setLineWidth(0.5)
        c.line(margin, y, ancho - margin, y)
        y -= (6 * mm)

        # Totales alineados a la derecha
        c.setFont(font_bold, 11)
        c.drawRightString(right_x, y, f"Total: ${_safe_float(total):.2f}")
        y -= (line_height + 2)
        c.setFont(font_main, 10)
        c.drawRightString(right_x, y, f"Tipo de pago: {tipo_pago}")
        y -= (line_height + 2)
        c.drawRightString(right_x, y, f"Monto recibido: ${_safe_float(monto_recibido):.2f}")
        y -= (line_height + 2)
        c.drawRightString(right_x, y, f"Cambio: ${_safe_float(cambio):.2f}")
        y -= (line_height + 4)

        # separador final y agradecimiento
        c.line(margin, y, ancho - margin, y)
        y -= (6 * mm)
        c.setFont(font_bold, 10)
        c.drawCentredString(ancho / 2, y, "¡Gracias por su compra!")
        y -= (4 * mm)
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(ancho / 2, y, "Technicell - Soporte y servicio técnico")

        # cerrar y salvar
        c.showPage()
        c.save()
    except Exception as e:
        logger.exception("Error generando PDF del ticket")
        try:
            if nombre_archivo.exists() and nombre_archivo.stat().st_size == 0:
                nombre_archivo.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"Error generando ticket PDF: {e}")

    # Verificación inmediata: archivo existe y tiene contenido
    try:
        if not nombre_archivo.exists():
            raise RuntimeError(f"No se pudo generar el ticket en: {nombre_archivo} (no existe)")
        size = nombre_archivo.stat().st_size
        if size == 0:
            raise RuntimeError(f"El ticket se generó pero tiene 0 bytes: {nombre_archivo}")
    except Exception as e:
        logger.exception("Verificación de archivo fallida")
        raise

    logger.debug("Ticket generado correctamente: %s (bytes=%s)", nombre_archivo, nombre_archivo.stat().st_size)
    return str(nombre_archivo)
