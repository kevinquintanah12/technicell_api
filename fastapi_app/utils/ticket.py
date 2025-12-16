from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import os
import re
from utils.ticket_counter import obtener_siguiente_numero_ticket

logger = logging.getLogger(__name__)

# A5 (horizontal/vertical) para tickets pequeños
A5 = (148 * mm, 210 * mm)


def _get_tickets_dir(path: Optional[str] = "tickets") -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / path).resolve()
    tickets_dir.mkdir(parents=True, exist_ok=True)
    return tickets_dir


def _sanitize_filename(name: str, max_len: int = 120) -> str:
    """
    Sanitiza el nombre de archivo:
    - Extrae basename (evita path traversal)
    - Reemplaza caracteres no seguros por underscore
    - Asegura extensión .pdf
    - Trunca longitud
    """
    if not name:
        return ""

    # basename para prevenir "../"
    name = os.path.basename(name)

    # Si no tiene extension .pdf al final, la añadimos
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"

    # Reemplazar caracteres no permitidos (permitir letras, números, guion bajo, guion, puntos)
    name = re.sub(r'[^A-Za-z0-9._\-]', '_', name)

    # Evitar empezar con punto
    if name.startswith('.'):
        name = f"ticket{name}"

    # Truncar manteniendo extension
    if len(name) > max_len:
        base, ext = os.path.splitext(name)
        base = base[: max_len - len(ext)]
        name = f"{base}{ext}"

    return name


def _unique_path_for(tickets_dir: Path, desired_name: str) -> Path:
    """
    Si desired_name ya existe en tickets_dir, añade sufijos _1, _2, ...
    Devuelve Path final (no crea archivo).
    """
    candidate = tickets_dir / desired_name
    if not candidate.exists():
        return candidate

    base, ext = os.path.splitext(desired_name)
    index = 1
    while True:
        new_name = f"{base}_{index}{ext}"
        candidate = tickets_dir / new_name
        if not candidate.exists():
            return candidate
        index += 1


def _draw_header_simple(
    c: canvas.Canvas,
    ancho: float,
    alto: float,
    margin: float,
    logo_full: Path,
    company: str,
    subtitle: str,
) -> float:
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


# ----------------- NUEVAS FUNCIONES PARA ESC/POS -----------------
# Estas funciones intentan usar python-escpos (escpos.printer)
# Si la librería no está disponible, lanzan una excepción clara.


def _ensure_escpos_available():
    try:
        import escpos.printer as _escpos_printer  # type: ignore
        return _escpos_printer
    except Exception as e:
        raise RuntimeError(
            "La librería 'python-escpos' no está disponible. Instálala con: pip install python-escpos Pillow"
        ) from e


def _print_escpos_with_printer(
    p,
    cliente_nombre: str,
    contacto: Optional[str],
    articulo: str,
    modelo: Optional[str],
    serie: Optional[str],
    falla_descripcion: str,
    observaciones: Optional[str],
    anticipo: float,
    total: float,
    equipo_id: Optional[int],
    company_name: str,
    logo_full: Optional[Path] = None,
):
    """
    Envía los textos a la impresora ya conectada (objeto escpos.printer.*).
    """
    try:
        # Cabecera
        try:
            p.set(align="center", bold=True, height=2, width=2)
        except Exception:
            try:
                p.set(align="center", bold=True)
            except Exception:
                pass
        p.text(f"{company_name}\n")
        p.text("Ingreso de reparación\n")
        p.text("-" * 32 + "\n")

        # Logo (intentar)
        if logo_full and logo_full.exists():
            try:
                p.image(str(logo_full))
            except Exception:
                # algunos backends requieren PIL.Image
                try:
                    from PIL import Image

                    im = Image.open(str(logo_full))
                    p.image(im)
                except Exception:
                    logger.debug("No se pudo imprimir logo en ESC/POS (se omitirá)")

        if equipo_id:
            p.text(f"ID Equipo: {equipo_id}\n")

        p.text(f"Cliente: {cliente_nombre}\n")
        if contacto:
            p.text(f"Contacto: {contacto}\n")

        p.text(f"Articulo: {articulo}\n")
        if modelo:
            p.text(f"Modelo: {modelo}\n")
        if serie:
            p.text(f"Serie/IMEI: {serie}\n")

        p.text("\nFalla:\n")
        p.text(f"{falla_descripcion}\n")

        if observaciones:
            p.text("\nObs:\n")
            p.text(f"{observaciones}\n")

        p.text("-" * 32 + "\n")
        if total and float(total):
            p.text(f"Total estimado: ${float(total):.2f}\n")
        if anticipo and float(anticipo):
            p.text(f"Anticipo: ${float(anticipo):.2f}\n")

        p.text("-" * 32 + "\n")
        p.text(datetime.now().strftime("%d/%m/%Y %H:%M") + "\n")

        p.feed(3)
        try:
            p.cut()
        except Exception:
            # Algunos dispositivos no soportan cut()
            pass

    except Exception as e:
        logger.exception("Error imprimiendo en impresora ESC/POS: %s", e)
        raise


def imprimir_ticket_escpos_from_data(
    cliente_nombre: str,
    contacto: Optional[str],
    articulo: str,
    modelo: Optional[str],
    serie: Optional[str],
    falla_descripcion: str,
    observaciones: Optional[str],
    anticipo: float,
    total: float,
    equipo_id: Optional[int],
    company_name: str,
    logo_full: Optional[Path],
    thermal_options: Dict[str, Any],
):
    """
    Conecta a la impresora térmica siguiendo thermal_options y envía el ticket.

    thermal_options esperadas (ejemplos):
      USB: {"type": "usb", "vid": 0x04b8, "pid": 0x0202, "in_ep": 0x82, "out_ep": 0x01}
      NETWORK: {"type": "network", "host": "192.168.1.50", "port": 9100}

    Lanza RuntimeError si falla la conexión o impresión.
    """
    escpos = _ensure_escpos_available()

    ttype = thermal_options.get("type", "network").lower()
    p = None
    try:
        if ttype == "usb":
            vid = int(thermal_options.get("vid"))
            pid = int(thermal_options.get("pid"))
            in_ep = thermal_options.get("in_ep")
            out_ep = thermal_options.get("out_ep")
            # Usb signature: Usb(vid, pid, timeout=0, in_ep=0x82, out_ep=0x01)
            if in_ep is not None and out_ep is not None:
                p = escpos.printer.Usb(vid, pid, in_ep=in_ep, out_ep=out_ep)
            else:
                p = escpos.printer.Usb(vid, pid)

        elif ttype == "network":
            host = thermal_options.get("host")
            port = int(thermal_options.get("port", 9100))
            p = escpos.printer.Network(host, port=port)

        elif ttype == "file":
            # Especial: escribir RAW bytes a un archivo (útil para debugging o para enviar a puerto)
            fname = thermal_options.get("path", "/tmp/escpos_out.bin")
            class FilePrinter:
                def __init__(self, path):
                    self._f = open(path, "ab")

                def text(self, txt):
                    self._f.write(txt.encode("utf-8", errors="replace"))

                def image(self, *a, **k):
                    pass

                def feed(self, n=1):
                    self._f.write(b"\n" * n)

                def cut(self):
                    pass

                def close(self):
                    self._f.close()

            p = FilePrinter(fname)

        else:
            raise RuntimeError(f"Tipo de conexión térmica desconocido: {ttype}")

        # enviar contenido
        _print_escpos_with_printer(
            p,
            cliente_nombre,
            contacto,
            articulo,
            modelo,
            serie,
            falla_descripcion,
            observaciones,
            anticipo,
            total,
            equipo_id,
            company_name,
            logo_full,
        )

        try:
            # cerrar si tiene método close
            if hasattr(p, "close"):
                p.close()
        except Exception:
            pass

    except Exception as e:
        logger.exception("Fallo al conectar/imprimir en impresora térmica: %s", e)
        raise RuntimeError(f"Error imprimiendo en impresora térmica: {e}") from e


# ----------------- FIN NUEVAS FUNCIONES ESC/POS -----------------


def generar_ticket_ingreso_reparacion(
    cliente_nombre: Optional[str] = None,
    contacto: Optional[str] = None,
    articulo: Optional[str] = None,
    modelo: Optional[str] = None,
    serie: Optional[str] = None,
    falla_descripcion: Optional[str] = None,
    observaciones: Optional[str] = None,
    anticipo: Optional[float] = 0.0,
    total: Optional[float] = 0.0,
    tipo_pago: Optional[str] = None,
    monto_recibido: Optional[float] = 0.0,
    cambio: Optional[float] = 0.0,
    tipo_ticket: str = "Físico",
    fecha_ingreso: Optional[datetime] = None,
    plazo_estimado: Optional[str] = None,
    path: str = "tickets",
    logo_path: str = "static/logogo.png",
    company_name: str = "TECHNICELL",
    ingreso: Optional[Dict[str, Any]] = None,
    equipo_id: Optional[int] = None,
    ticket_name: Optional[str] = None,  # <-- nuevo parámetro opcional que puede venir de Flutter
    # NUEVOS PARAMS
    print_thermal: bool = False,
    thermal_options: Optional[Dict[str, Any]] = None,
    throw_on_print_error: bool = False,
) -> str:
    """
    Genera un ticket PDF de ingreso/recepción para reparación.
    Si se provee `ticket_name`, se usa (después de sanitizar). Si no, se genera
    un nombre por defecto usando el número de ticket y (opcional) equipo_id.
    Devuelve la ruta absoluta al archivo creado.

    Si `print_thermal` es True, intentará además imprimir en una impresora térmica
    usando `thermal_options`. Por defecto, cualquier fallo de impresión se registrará
    y no impedirá la creación del PDF; si `throw_on_print_error` es True, entonces
    se lanzará RuntimeError en caso de fallo de impresión.
    """
    # Sobreescribir valores si ingreso es dict
    if ingreso and isinstance(ingreso, dict):
        cliente_nombre = cliente_nombre or ingreso.get("cliente_nombre") or ingreso.get("nombre_cliente")
        contacto = contacto or ingreso.get("telefono") or ingreso.get("contacto")
        articulo = articulo or ingreso.get("articulo") or ingreso.get("equipo") or ingreso.get("marca")
        modelo = modelo or ingreso.get("modelo")
        serie = serie or ingreso.get("imei") or ingreso.get("serie")
        falla_descripcion = falla_descripcion or ingreso.get("falla") or ingreso.get("falla_reportada")
        observaciones = observaciones or ingreso.get("observaciones")
        anticipo = anticipo if anticipo not in (None,) else ingreso.get("anticipo", 0.0)
        total = total if total not in (None,) else ingreso.get("total_estimado", ingreso.get("total", 0.0))
        tipo_pago = tipo_pago or ingreso.get("tipo_pago")
        monto_recibido = monto_recibido if monto_recibido not in (None,) else ingreso.get("monto_recibido", 0.0)
        cambio = cambio if cambio not in (None,) else ingreso.get("cambio", 0.0)
        fecha_ingreso = fecha_ingreso or ingreso.get("fecha_ingreso")
        equipo_id = equipo_id or ingreso.get("equipo_id")  # <-- tomar equipo_id del dict si existe

    fecha_ingreso = fecha_ingreso or datetime.now()
    cliente_nombre = cliente_nombre or "Cliente"
    articulo = articulo or "Artículo"
    falla_descripcion = falla_descripcion or "No especificada"

    tickets_dir = _get_tickets_dir(path)
    numero_ticket = obtener_siguiente_numero_ticket(tickets_dir)

    # ------------- Determinar nombre de archivo seguro -------------
    # Si Flutter nos pasa ticket_name -> sanitizearlo y asegurar .pdf
    safe_name = None
    if ticket_name:
        safe_name = _sanitize_filename(ticket_name)
        # si el nombre quedó vacío por alguna razón, lo ignoramos y generamos uno por defecto
        if not safe_name:
            safe_name = None

    # Si no se proporcionó ticket_name válido -> construir por defecto
    if not safe_name:
        if equipo_id:
            default_name = f"ticket_ingreso_reparacion_{numero_ticket}_equipo{equipo_id}.pdf"
        else:
            default_name = f"ticket_ingreso_reparacion_{numero_ticket}.pdf"
        safe_name = _sanitize_filename(default_name)

    # Obtener ruta final única (si ya existe, añade sufijo _1, _2...)
    nombre_archivo = _unique_path_for(tickets_dir, safe_name)

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

        # ID del equipo
        if equipo_id:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(left_x, y, "ID Equipo:")
            c.setFont("Helvetica", 9)
            c.drawString(left_x + 28 * mm, y, str(equipo_id))
            y -= line_h

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

        # Falla / descripcion (wrap)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Falla reportada:")
        y -= (line_h - 2 * mm)
        c.setFont("Helvetica", 9)
        text = c.beginText(left_x, y)
        text.setFont("Helvetica", 9)
        for ln in _wrap_text(str(falla_descripcion), 48):
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

        # Cobro
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
            y -= (2 * mm)

        # Fecha / tipo de ticket / plazo
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

        # Pie y cláusula
        c.setLineWidth(0.4)
        c.line(left_x, y, right_x, y)
        y -= 6 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(ancho / 2, y, "IMPORTANTE")
        y -= 5 * mm
        c.setFont("Helvetica", 8)
        aviso_lines = [
            "El artículo se entregará junto con el ticket físico o electrónico.",
            "Sin embargo, el ticket electrónico NO tiene garantía. Conserva tu ticket.",
            "El tiempo de reparación será tomado en consideración al momento de resolver la incidencia.",
        ]
        for ln in aviso_lines:
            for sub in _wrap_text(ln, 60):
                c.drawCentredString(ancho / 2, y, sub)
                y -= 4.5 * mm
        y -= 4 * mm
        c.setFont("Helvetica", 9)
        c.drawString(left_x, y, "Recibido por (firma): ____________________________")
        y -= 10 * mm
        c.drawString(left_x, y, "Entrega prevista (firma cliente): __________________")
        y -= 10 * mm
        c.setFont("Helvetica-Oblique", 8)
        c.drawCentredString(ancho / 2, margin + 6 * mm, f"{company_name} - Servicio técnico")

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

    if not nombre_archivo.exists() or nombre_archivo.stat().st_size == 0:
        raise RuntimeError("No se pudo generar el ticket de ingreso (archivo vacío o inexistente)")

    logger.debug("Ticket ingreso generado: %s", nombre_archivo)

    # Si se pidió impresión térmica, intentarlo (pero PDF ya generado)
    if print_thermal:
        try:
            if not thermal_options:
                raise RuntimeError("Se solicitó impresión térmica pero no se proporcionaron 'thermal_options'.")

            # Llamada a la función que gestiona conexión e impresión
            imprimir_ticket_escpos_from_data(
                cliente_nombre=cliente_nombre,
                contacto=contacto,
                articulo=articulo,
                modelo=modelo,
                serie=serie,
                falla_descripcion=falla_descripcion,
                observaciones=observaciones,
                anticipo=anticipo or 0.0,
                total=total or 0.0,
                equipo_id=equipo_id,
                company_name=company_name,
                logo_full=logo_full if logo_full.exists() else None,
                thermal_options=thermal_options,
            )
        except Exception as e:
            logger.exception("Fallo en impresión térmica: %s", e)
            if throw_on_print_error:
                raise

    return str(nombre_archivo)


def _wrap_text(text: str, max_chars: int):
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
