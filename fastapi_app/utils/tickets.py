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


def generar_ticket_venta_multiple(
    detalles: List[Any],
    total: float,
    tipo_pago: str,
    monto_recibido: float,
    cambio: float,
    path: str = "tickets",
    logo_path: str = "static/logo.png"
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

    # Intentamos crear el PDF de forma robusta
    try:
        c = canvas.Canvas(str(nombre_archivo), pagesize=A5)
        # Logo (opcional)
        logo_full = Path(__file__).resolve().parent.parent / logo_path
        if logo_full.exists():
            try:
                logo_w = 50
                logo_h = 50
                c.drawImage(str(logo_full), x=(ancho - logo_w) / 2, y=alto - 60, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                logger.exception("No se pudo dibujar el logo en el ticket")

        # Encabezado
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(ancho / 2, alto - 70, "🌟 TECHNICELL 🌟")
        c.setFont("Helvetica", 10)
        c.drawCentredString(ancho / 2, alto - 85, "Recibo de venta")
        c.line(10, alto - 90, ancho - 10, alto - 90)

        fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        c.setFont("Helvetica", 10)
        c.drawString(15, alto - 105, f"Fecha: {fecha_str}")

        y = alto - 125
        c.setFont("Helvetica-Bold", 11)
        c.drawString(15, y, "Productos:")
        y -= 14
        c.setFont("Helvetica", 10)

        for raw in detalles_list:
            d = _to_detalle_dict(raw)
            cantidad = int(d.get("cantidad") or 1)
            precio_unit = _safe_float(d.get("precio_unitario"))
            subtotal = d.get("subtotal")
            if subtotal is None:
                subtotal = cantidad * precio_unit
            subtotal = _safe_float(subtotal)
            producto_nombre = (d.get("producto") or d.get("producto_nombre") or "Producto")

            linea = f"{producto_nombre} x{cantidad}  -  ${precio_unit:.2f}"
            c.drawString(15, y, linea)
            c.drawRightString(ancho - 15, y, f"${subtotal:.2f}")
            y -= 14

            if y < 80:
                c.showPage()
                y = alto - 40
                c.setFont("Helvetica", 10)

        y -= 6
        c.line(10, y, ancho - 10, y)
        y -= 18

        total_safe = _safe_float(total)
        monto_recibido_safe = _safe_float(monto_recibido)
        cambio_safe = _safe_float(cambio)

        c.setFont("Helvetica-Bold", 11)
        c.drawString(15, y, f"Total: ${total_safe:.2f}")
        y -= 14
        c.setFont("Helvetica", 11)
        c.drawString(15, y, f"Tipo de pago: {tipo_pago}")
        y -= 14
        c.drawString(15, y, f"Monto recibido: ${monto_recibido_safe:.2f}")
        y -= 14
        c.drawString(15, y, f"Cambio: ${cambio_safe:.2f}")
        y -= 20

        c.line(10, y, ancho - 10, y)
        y -= 18
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(ancho / 2, y, "¡Gracias por su compra!")
        y -= 12
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(ancho / 2, y, "Technicell - Soporte y servicio técnico")

        # Asegurarnos de escribir y cerrar el canvas
        c.showPage()
        c.save()
    except Exception as e:
        logger.exception("Error generando PDF del ticket")
        # Si hay un archivo corrupto, intentar eliminarlo para evitar basura
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
