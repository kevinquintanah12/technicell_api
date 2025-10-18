from reportlab.lib.pagesizes import A5
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
import os

def generar_ticket_profesional(cobro, path="tickets", logo_path="static/logo.png"):
    """
    Genera un ticket PDF profesional para un cobro,
    con datos completos del cliente y del equipo/producto.
    """
    os.makedirs(path, exist_ok=True)
    nombre_archivo = f"{path}/ticket_{cobro.id}.pdf"
    
    c = canvas.Canvas(nombre_archivo, pagesize=A5)
    ancho, alto = A5

    # -------------------
    # Logo de la empresa
    # -------------------
    if os.path.exists(logo_path):
        logo_width = 50  # ancho en puntos
        logo_height = 50  # alto en puntos
        c.drawImage(
            logo_path,
            x=(ancho - logo_width) / 2,  # centrar horizontal
            y=alto - 60,  # distancia desde arriba
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask='auto'
        )

    # -------------------
    # Encabezado
    # -------------------
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(ancho / 2, alto - 70, "🌟 TECHNICELL 🌟")
    c.setFont("Helvetica", 10)
    c.drawCentredString(ancho / 2, alto - 85, "Recibo de pago")
    c.line(10, alto - 90, ancho - 10, alto - 90)

    # -------------------
    # Información del cliente
    # -------------------
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

    # -------------------
    # Información del equipo/producto
    # -------------------
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

    # Línea separadora
    c.line(10, y, ancho - 10, y)
    y -= 15

    # -------------------
    # Detalles de pago
    # -------------------
    c.setFont("Helvetica", 12)
    c.drawString(15, y, f"Monto total: ${cobro.monto_total:.2f}")
    y -= 15
    c.drawString(15, y, f"Anticipo: ${cobro.anticipo:.2f}")
    y -= 15
    c.drawString(15, y, f"Saldo pendiente: ${cobro.saldo_pendiente:.2f}")
    y -= 15
    c.drawString(15, y, f"Método de pago: {cobro.metodo_pago}")
    y -= 15
    c.drawString(15, y, f"Fecha de pago: {cobro.fecha_pago.strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 20

    # Línea separadora
    c.line(10, y, ancho - 10, y)
    y -= 20

    # -------------------
    # Pie de página
    # -------------------
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(ancho / 2, y, "¡Gracias por su pago!")
    y -= 15
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(ancho / 2, y, "Technicell - Soporte y servicio técnico")

    # Guardar PDF
    c.showPage()
    c.save()
    
    return nombre_archivo
