# routers/detalle_cobro.py
from typing import List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from database import get_db
from crud import detalle_cobro as crud_detalle
from utils.tickets import generar_ticket_venta_multiple
from utils.ticket import generar_ticket_ingreso_reparacion

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    try:
        # Leer body
        try:
            body = await request.json()
        except Exception:
            body = None

        # ¿Es reparación? (acepta body o query param)
        es_reparacion = False
        if isinstance(body, dict):
            es_reparacion = bool(body.get("es_reparacion", False))

        if request.query_params.get("es_reparacion"):
            es_reparacion = request.query_params.get("es_reparacion").lower() == "true"

        # Obtener detalles y parámetros de pago
        if isinstance(body, list):
            detalles_payload = body
            tipo_pago = request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(request.query_params.get("monto_recibido", 0.0))

        elif isinstance(body, dict):
            detalles_payload = body.get("detalles") or []
            tipo_pago = body.get("tipo_pago") or request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(
                body.get("monto_recibido", request.query_params.get("monto_recibido", 0.0))
                or 0.0
            )

            # Si viene un solo detalle sin "detalles"
            if not detalles_payload and ("producto_id" in body and "cantidad" in body):
                detalles_payload = [body]

        else:
            raise HTTPException(status_code=400, detail="Formato de body inválido")

        logger.debug("Request recibida: detalles=%s tipo_pago=%s monto_recibido=%s es_reparacion=%s",
                     detalles_payload, tipo_pago, monto_recibido, es_reparacion)

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles")

        # Registrar en BD
        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)

        lista_detalles = resultado.get("detalles", [])
        total = float(resultado.get("total_general", resultado.get("total", 0.0)))

        monto_recibido_safe = float(monto_recibido or 0.0)
        cambio = max(0.0, monto_recibido_safe - total) if tipo_pago.lower() == "efectivo" else 0.0

        # ──────────────────────────────────────────
        #   SELECCIONAR TICKET SEGÚN EL TIPO
        # ──────────────────────────────────────────
        try:
            if es_reparacion:
                ticket_path = generar_ticket_ingreso_reparacion(
                    detalles=lista_detalles,
                    total=total,
                    tipo_pago=tipo_pago,
                    monto_recibido=monto_recibido_safe,
                    cambio=cambio
                )
            else:
                ticket_path = generar_ticket_venta_multiple(
                    detalles=lista_detalles,
                    total=total,
                    tipo_pago=tipo_pago,
                    monto_recibido=monto_recibido_safe,
                    cambio=cambio
                )

        except Exception as e:
            logger.exception("Fallo al generar ticket PDF")
            raise HTTPException(
                status_code=500,
                detail=f"Venta/Ingreso registrado pero error generando ticket: {e}"
            )

        # Verificar archivo
        ticket_name = os.path.basename(ticket_path)
        file_path = Path(ticket_path)

        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Ticket generado pero archivo no encontrado")

        file_size = file_path.stat().st_size
        if file_size == 0:
            raise HTTPException(status_code=500, detail="Ticket generado pero el archivo está vacío")

        # URL para descargar
        base = str(request.base_url).rstrip("/")
        ticket_url = f"{base}/detalle_cobro/ticket/{ticket_name}"

        return {
            "detalles": lista_detalles,
            "total": total,
            "es_reparacion": es_reparacion,
            "ticket": ticket_name,
            "ticket_url": ticket_url,
            "ticket_path": str(file_path.resolve()),
            "ticket_size_bytes": file_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando detalles de cobro")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    safe_name = os.path.basename(ticket_name)
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / "tickets").resolve()
    file_path = tickets_dir / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return FileResponse(str(file_path), media_type="application/pdf", filename=safe_name)
