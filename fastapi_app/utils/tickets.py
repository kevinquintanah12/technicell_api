# utils/tickets.py
from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
import os
from typing import List, Any

def generar_ticket_profesional(cobro, path="tickets", logo_path="static/logo.png"):
    """
    Genera un ticket PDF profesional para un cobro,
    con datos completos del cliente y del equipo/producto.
    (Tu función original; la dejo igual funcionalmente).
    """
    os.makedirs(path, exist_ok=True)
    nombre_archivo = f"{path}/ticket_{cobro.id}.pdf"
    
    c = canvas.Canvas(nombre_archivo, pagesize=A5)
    ancho, alto = A5

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

    # Cliente
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

    # Equipo/Producto
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

    # Separador
    c.line(10, y, ancho - 10, y)
    y -= 15

    # Detalles de pago
    c.setFont("Helvetica", 12)
    c.drawString(15, y, f"Monto total: ${cobro.monto_total:.2f}")
    y -= 15
    c.drawString(15, y, f"Anticipo: ${cobro.anticipo:.2f}")
    y -= 15
    c.drawString(15, y, f"Saldo pendiente: ${cobro.saldo_pendiente:.2f}")
    y -= 15
    c.drawString(15, y, f"Método de pago: {cobro.metodo_pago}")
    y -= 15
    # fecha_pago puede ser None; proteger
    try:
        fecha_str = cobro.fecha_pago.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        fecha_str = "-"
    c.drawString(15, y, f"Fecha de pago: {fecha_str}")
    y -= 20

    c.line(10, y, ancho - 10, y)
    y -= 20

    # Pie
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(ancho / 2, y, "¡Gracias por su pago!")
    y -= 15
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(ancho / 2, y, "Technicell - Soporte y servicio técnico")

    c.showPage()
    c.save()
    
    return nombre_archivo


def generar_ticket_venta_multiple(detalles: List[Any], total: float, tipo_pago: str, monto_recibido: float, cambio: float, path="tickets", logo_path="static/logo.png"):
    """
    Genera ticket PDF para una venta con varios detalles.
    detalles: lista de dicts u objetos resultantes de tu CRUD.
      Se intenta extraer: nombre del producto, cantidad, precio_unitario o subtotal.
    Devuelve la ruta del PDF generado (por ejemplo "tickets/ticket_venta_20251119_112500.pdf").
    """
    os.makedirs(path, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"{path}/ticket_venta_{timestamp}.pdf"

    ancho, alto = A5
    c = canvas.Canvas(nombre_archivo, pagesize=A5)

    # Logo (opcional)
    if os.path.exists(logo_path):
        logo_w = 50
        logo_h = 50
        c.drawImage(logo_path, x=(ancho - logo_w) / 2, y=alto - 60, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')

    # Encabezado
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(ancho / 2, alto - 70, "🌟 TECHNICELL 🌟")
    c.setFont("Helvetica", 10)
    c.drawCentredString(ancho / 2, alto - 85, "Recibo de venta")
    c.line(10, alto - 90, ancho - 10, alto - 90)

    # Fecha
    fecha_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 10)
    c.drawString(15, alto - 105, f"Fecha: {fecha_str}")

    # Productos
    y = alto - 125
    c.setFont("Helvetica-Bold", 11)
    c.drawString(15, y, "Productos:")
    y -= 14
    c.setFont("Helvetica", 10)

    for d in detalles:
        # extraer nombre del producto robustamente
        producto_nombre = None
        cantidad = 1
        precio_unit = None
        subtotal = None

        # si es objeto SQLAlchemy
        try:
            if hasattr(d, "producto") and getattr(d, "producto") is not None:
                producto = getattr(d, "producto")
                producto_nombre = getattr(producto, "nombre", None)
        except Exception:
            producto_nombre = None

        # si es dict o no se obtuvo nombre
        if producto_nombre is None:
            if isinstance(d, dict):
                # varios posibles campos
                producto_nombre = d.get("producto_nombre") or (d.get("producto") and (d.get("producto").get("nombre") if isinstance(d.get("producto"), dict) else None))
                cantidad = d.get("cantidad", cantidad)
                precio_unit = d.get("precio_unitario") or d.get("precio")
                subtotal = d.get("subtotal")
            else:
                producto_nombre = getattr(d, "producto_nombre", None) or getattr(d, "nombre", None)
                cantidad = getattr(d, "cantidad", cantidad)
                precio_unit = getattr(d, "precio_unitario", None) or getattr(d, "precio", None)
                subtotal = getattr(d, "subtotal", None)

        # calcular subtotal si falta
        try:
            if subtotal is None:
                subtotal = float(cantidad) * float(precio_unit) if precio_unit is not None else 0.0
        except Exception:
            subtotal = 0.0

        producto_nombre = producto_nombre or "Producto"
        linea = f"{producto_nombre} x{int(cantidad)}  -  ${float(precio_unit) if precio_unit is not None else 0.0:.2f}"
        c.drawString(15, y, linea)
        c.drawRightString(ancho - 15, y, f"${subtotal:.2f}")
        y -= 14

        if y < 80:
            c.showPage()
            y = alto - 40
            c.setFont("Helvetica", 10)

    # Separador
    y -= 6
    c.line(10, y, ancho - 10, y)
    y -= 18

    # Totales y pago
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
