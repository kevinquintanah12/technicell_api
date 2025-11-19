from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
import os
from typing import List, Any

# ❗ DEFINIR A5 MANUALMENTE
A5 = (148 * mm, 210 * mm)


def generar_ticket_profesional(cobro, path="tickets", logo_path="static/logo.png"):
    os.makedirs(path, exist_ok=True)
    nombre_archivo = f"{path}/ticket_{cobro.id}.pdf"
    
    ancho, alto = A5
    c = canvas.Canvas(nombre_archivo, pagesize=A5)

    # Logo
    if os.path.exists(logo_path):
        logo_width = 50
        logo_height = 50
        c.drawImage(
            logo_path,
            x=(ancho - logo_width) / 2,
            y=alto - 60,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask='auto'
        )

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(ancho / 2, alto - 70, "🌟 TECHNICELL 🌟")
    c.setFont("Helvetica", 10)
    c.drawCentredString(ancho / 2, alto - 85, "Recibo de pago")
    c.line(10, alto - 90, ancho - 10, alto - 90)

    cliente = cobro.cliente
    c.setFont("Helvetica-Bold", 12)
    y = alto - 110
    c.drawString(15, y, f"Cliente: {cliente.nombre_completo}")
    y -= 15

    if hasattr(cliente, "telefono") and cliente.telefono:
        c.drawString(15, y, f"Teléfono: {cliente.telefono}")
        y -= 15
    if hasattr(cliente, "email") and cliente.email:
        c.drawString(15, y, f"Email: {cliente.email}")
        y -= 15

    equipo = cobro.equipo
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15, y, "Equipo/Producto:")
    y -= 15

    if hasattr(equipo, "marca"):
        c.drawString(20, y, f"Marca: {equipo.marca}")
        y -= 15
    if hasattr(equipo, "modelo"):
        c.drawString(20, y, f"Modelo: {equipo.modelo}")
        y -= 15
    if hasattr(equipo, "fallo"):
        c.drawString(20, y, f"Fallo: {equipo.fallo}")
        y -= 15

    c.line(10, y, ancho - 10, y)
    y -= 15

    c.setFont("Helvetica", 12)
    c.drawString(15, y, f"Monto total: ${cobro.monto_total:.2f}")
    y -= 15
    c.drawString(15, y, f"Anticipo: ${cobro.anticipo:.2f}")
    y -= 15
    c.drawString(15, y, f"Saldo pendiente: ${cobro.saldo_pendiente:.2f}")
    y -= 15
    c.drawString(15, y, f"Método de pago: {cobro.metodo_pago}")
    y -= 15

    try:
        fecha_str = cobro.fecha_pago.strftime('%Y-%m-%d %H:%M:%S')
    except:
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



def generar_ticket_venta_multiple(detalles: List[Any], total: float, tipo_pago: str, monto_recibido: float, cambio: float, path="tickets", logo_path="static/logo.png"):
    os.makedirs(path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{path}/ticket_venta_{timestamp}.pdf"

    ancho, alto = A5
    c = canvas.Canvas(nombre_archivo, pagesize=A5)

    if os.path.exists(logo_path):
        logo_w = 50
        logo_h = 50
        c.drawImage(logo_path, x=(ancho - logo_w) / 2, y=alto - 60,
                     width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')

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

    for d in detalles:
        producto_nombre = None
        cantidad = 1
        precio_unit = None
        subtotal = None

        if hasattr(d, "producto"):
            prod = getattr(d, "producto")
            if prod:
                producto_nombre = getattr(prod, "nombre", None)

        if producto_nombre is None and isinstance(d, dict):
            producto_nombre = d.get("producto_nombre") or (
                d.get("producto") and d.get("producto").get("nombre")
            )
            cantidad = d.get("cantidad", 1)
            precio_unit = d.get("precio_unitario") or d.get("precio")
            subtotal = d.get("subtotal")

        if subtotal is None:
            try:
                subtotal = float(cantidad) * float(precio_unit)
            except:
                subtotal = 0.0

        producto_nombre = producto_nombre or "Producto"

        linea = f"{producto_nombre} x{int(cantidad)}  -  ${float(precio_unit) if precio_unit else 0.00:.2f}"
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

    c.setFont("Helvetica-Bold", 11)
    c.drawString(15, y, f"Total: ${total:.2f}")
    y -= 14
    c.setFont("Helvetica", 11)
    c.drawString(15, y, f"Tipo de pago: {tipo_pago}")
    y -= 14
    c.drawString(15, y, f"Monto recibido: ${monto_recibido:.2f}")
    y -= 14
    c.drawString(15, y, f"Cambio: ${cambio:.2f}")
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
