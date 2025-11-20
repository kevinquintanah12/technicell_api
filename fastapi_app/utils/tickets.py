from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
import os
from typing import List, Any, Dict, Optional

# Definir A5 manualmente (ReportLab puede no exponer A5 directamente)
A5 = (148 * mm, 210 * mm)


def _to_detalle_dict(d: Any) -> Dict[str, Any]:
    """
    Normaliza un 'detalle' que puede venir como:
      - dict (ej: {"producto": "Cable", "cantidad": 2, "subtotal": 100})
      - objeto ORM / objeto con atributos (producto, cantidad, subtotal, producto.nombre, etc.)
    Devuelve un dict con claves: producto (nombre), cantidad, precio_unitario, subtotal.
    """
    detalle = {"producto": None, "cantidad": 1, "precio_unitario": None, "subtotal": None}

    # Si ya es dict, usarlo directamente (con get para no fallar)
    if isinstance(d, dict):
        detalle["producto"] = d.get("producto") or d.get("producto_nombre") or (
            d.get("producto") and (d.get("producto").get("nombre") if isinstance(d.get("producto"), dict) else None)
        )
        detalle["cantidad"] = d.get("cantidad", detalle["cantidad"])
        detalle["precio_unitario"] = d.get("precio_unitario") or d.get("precio") or d.get("precio_venta")
        detalle["subtotal"] = d.get("subtotal")
        return detalle

    # Si tiene atributos (objeto SQLAlchemy u otro)
    try:
        # intento obtener producto (puede ser objeto o nombre)
        prod = getattr(d, "producto", None)
        if prod is not None:
            # si producto es objeto con nombre
            nombre_prod = getattr(prod, "nombre", None) if not isinstance(prod, str) else prod
            detalle["producto"] = nombre_prod or str(prod)
        else:
            # buscar directamente atributos de nombre
            detalle["producto"] = getattr(d, "producto_nombre", None) or getattr(d, "nombre", None)
    except Exception:
        detalle["producto"] = None

    # cantidad
    try:
        detalle["cantidad"] = getattr(d, "cantidad", detalle["cantidad"])
    except Exception:
        detalle["cantidad"] = detalle["cantidad"]

    # precio_unitario
    try:
        detalle["precio_unitario"] = getattr(d, "precio_unitario", None) or getattr(d, "precio", None) or getattr(d, "precio_venta", None)
    except Exception:
        detalle["precio_unitario"] = None

    # subtotal
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


def generar_ticket_profesional(cobro, path="tickets", logo_path="static/logo.png"):
    """
    Genera un ticket (recibo de cobro) profesional a partir de un objeto 'cobro'.
    Se espera que 'cobro' tenga atributos: id, cliente (con nombre_completo, telefono, email),
    equipo (marca, modelo, fallo), monto_total, anticipo, saldo_pendiente, metodo_pago, fecha_pago.
    """
    os.makedirs(path, exist_ok=True)
    nombre_archivo = f"{path}/ticket_{getattr(cobro, 'id', datetime.now().timestamp())}.pdf"

    ancho, alto = A5
    c = canvas.Canvas(nombre_archivo, pagesize=A5)

    # Logo
    if os.path.exists(logo_path):
        logo_width = 50
        logo_height = 50
        try:
            c.drawImage(
                logo_path,
                x=(ancho - logo_width) / 2,
                y=alto - 60,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        except Exception:
            # no hacer nada si falla la imagen
            pass

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(ancho / 2, alto - 70, "🌟 TECHNICELL 🌟")
    c.setFont("Helvetica", 10)
    c.drawCentredString(ancho / 2, alto - 85, "Recibo de pago")
    c.line(10, alto - 90, ancho - 10, alto - 90)

    cliente = getattr(cobro, "cliente", None)
    c.setFont("Helvetica-Bold", 12)
    y = alto - 110
    nombre_cliente = getattr(cliente, "nombre_completo", None) if cliente else getattr(cobro, "cliente_nombre", None)
    c.drawString(15, y, f"Cliente: {nombre_cliente or '-'}")
    y -= 15

    if cliente:
        telefono = getattr(cliente, "telefono", None)
        email = getattr(cliente, "email", None)
        if telefono:
            c.drawString(15, y, f"Teléfono: {telefono}")
            y -= 15
        if email:
            c.drawString(15, y, f"Email: {email}")
            y -= 15

    equipo = getattr(cobro, "equipo", None)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15, y, "Equipo/Producto:")
    y -= 15
    if equipo:
        if getattr(equipo, "marca", None):
            c.drawString(20, y, f"Marca: {getattr(equipo, 'marca')}")
            y -= 15
        if getattr(equipo, "modelo", None):
            c.drawString(20, y, f"Modelo: {getattr(equipo, 'modelo')}")
            y -= 15
        if getattr(equipo, "fallo", None):
            c.drawString(20, y, f"Fallo: {getattr(equipo, 'fallo')}")
            y -= 15

    c.line(10, y, ancho - 10, y)
    y -= 15

    c.setFont("Helvetica", 12)
    monto_total = _safe_float(getattr(cobro, "monto_total", None))
    anticipo = _safe_float(getattr(cobro, "anticipo", None))
    saldo = _safe_float(getattr(cobro, "saldo_pendiente", None))
    c.drawString(15, y, f"Monto total: ${monto_total:.2f}")
    y -= 15
    c.drawString(15, y, f"Anticipo: ${anticipo:.2f}")
    y -= 15
    c.drawString(15, y, f"Saldo pendiente: ${saldo:.2f}")
    y -= 15
    c.drawString(15, y, f"Método de pago: {getattr(cobro, 'metodo_pago', '-')}")
    y -= 15

    try:
        fecha_str = getattr(cobro, "fecha_pago", None)
        if fecha_str:
            fecha_str = fecha_str.strftime('%Y-%m-%d %H:%M:%S')
        else:
            fecha_str = "-"
    except Exception:
        fecha_str = "-"
    c.drawString(15, y, f"Fecha de pago: {fecha_str}")
    y -= 20

    c.line(10, y, ancho - 10, y)
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(ancho / 2, y, "¡Gracias por su pago!")
    y -= 15
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(ancho / 2, y, "Technicell - Soporte y servicio técnico")

    c.showPage()
    c.save()

    return nombre_archivo


def generar_ticket_venta_multiple(
    detalles: List[Any],
    total: float,
    tipo_pago: str,
    monto_recibido: float,
    cambio: float,
    path="tickets",
    logo_path="static/logo.png"
):
    """
    Genera un ticket PDF para una venta con varios detalles.

    `detalles` puede ser:
      - lista de dicts
      - lista de objetos ORM
      - o incluso el dict que devuelva tu CRUD: {"detalles": [...], "total_general": X}
    La función normaliza cada elemento con _to_detalle_dict y asegura que no haya iteraciones
    sobre claves (lo que provocaba 'str' object has no attribute 'get').
    """
    os.makedirs(path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{path}/ticket_venta_{timestamp}.pdf"

    # Si el usuario pasó directamente el resultado del CRUD (dict con 'detalles')
    if isinstance(detalles, dict) and "detalles" in detalles:
        detalles_list = detalles.get("detalles", [])
    else:
        detalles_list = detalles or []

    ancho, alto = A5
    c = canvas.Canvas(nombre_archivo, pagesize=A5)

    # Logo (opcional)
    if os.path.exists(logo_path):
        try:
            logo_w = 50
            logo_h = 50
            c.drawImage(logo_path, x=(ancho - logo_w) / 2, y=alto - 60, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

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

    # Recorremos la lista de detalles: cada elemento será normalizado a dict
    for raw in detalles_list:
        d = _to_detalle_dict(raw)

        cantidad = int(d.get("cantidad") or 1)
        precio_unit = _safe_float(d.get("precio_unitario"))
        subtotal = d.get("subtotal")
        if subtotal is None:
            subtotal = cantidad * precio_unit
        subtotal = _safe_float(subtotal)

        producto_nombre = d.get("producto") or "Producto"

        # Línea de producto
        try:
            linea = f"{producto_nombre} x{cantidad}  -  ${precio_unit:.2f}"
        except Exception:
            linea = f"{producto_nombre} x{cantidad}  -  $0.00"

        c.drawString(15, y, linea)
        c.drawRightString(ancho - 15, y, f"${subtotal:.2f}")
        y -= 14

        # Nueva página si hace falta
        if y < 80:
            c.showPage()
            y = alto - 40
            c.setFont("Helvetica", 10)

    # Separador y totales
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

    c.showPage()
    c.save()

    return nombre_archivo
