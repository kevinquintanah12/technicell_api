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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    try:
        try:
            body = await request.json()
        except Exception:
            body = None

        if isinstance(body, list):
            detalles_payload = body
            tipo_pago = request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(request.query_params.get("monto_recibido", 0.0))
        elif isinstance(body, dict):
            detalles_payload = body.get("detalles") or []
            tipo_pago = body.get("tipo_pago") or request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(body.get("monto_recibido", request.query_params.get("monto_recibido", 0.0) or 0.0))
            if not detalles_payload and ("producto_id" in body and "cantidad" in body):
                detalles_payload = [body]
        else:
            raise HTTPException(status_code=400, detail="Formato de body inválido")

        logger.debug("Request recibida: detalles=%s tipo_pago=%s monto_recibido=%s", detalles_payload, tipo_pago, monto_recibido)

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles")

        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)

        lista_detalles = resultado.get("detalles", [])
        total = float(resultado.get("total_general", resultado.get("total", 0.0)))

        monto_recibido_safe = float(monto_recibido or 0.0)
        cambio = 0.0
        if str(tipo_pago).lower() == "efectivo":
            cambio = max(0.0, monto_recibido_safe - total)

        # Intentar generar ticket (capturamos excepciones claras)
        try:
            ticket_path = generar_ticket_venta_multiple(
                detalles=lista_detalles,
                total=total,
                tipo_pago=tipo_pago,
                monto_recibido=monto_recibido_safe,
                cambio=cambio
            )
        except Exception as e:
            logger.exception("Fallo al generar ticket PDF")
            # Devolver respuesta parcial con detalle para debug
            raise HTTPException(status_code=500, detail=f"Venta registrada pero error generando ticket: {e}")

        ticket_name = os.path.basename(ticket_path)

        # Verificar que el archivo realmente exista y tenga bytes
        try:
            file_path = Path(ticket_path)
            if not file_path.exists():
                raise HTTPException(status_code=500, detail="Ticket generado pero archivo no encontrado en servidor")
            file_size = file_path.stat().st_size
            if file_size == 0:
                raise HTTPException(status_code=500, detail="Ticket generado pero el archivo está vacío (0 bytes)")
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error verificando archivo del ticket")
            raise HTTPException(status_code=500, detail="Error verificando ticket en servidor")

        base = str(request.base_url).rstrip("/")
        ticket_url = f"{base}/detalle-cobro{router.prefix}/ticket/{ticket_name}"


        # Respuesta con info adicional útil para debug (puedes quitar size/abs_path en prod)
        return {
            "detalles": lista_detalles,
            "total": total,
            "ticket": ticket_name,
            "ticket_url": ticket_url,
            "ticket_path": str(file_path.resolve()),
            "ticket_size_bytes": file_size
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
