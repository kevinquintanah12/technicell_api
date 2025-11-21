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
router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    try:
        try:
            body = await request.json()
        except:
            body = None

        # Soporta body como lista o como objeto
        if isinstance(body, list):
            detalles_payload = body
            tipo_pago = request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(request.query_params.get("monto_recibido", 0.0))

        elif isinstance(body, dict):
            detalles_payload = body.get("detalles") or []
            tipo_pago = body.get("tipo_pago") or request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(body.get("monto_recibido", request.query_params.get("monto_recibido", 0.0)))

            if not detalles_payload and ("producto_id" in body and "cantidad" in body):
                detalles_payload = [body]  # Caso legacy

        else:
            raise HTTPException(status_code=400, detail="Formato de body inválido")

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles")

        # ✔ CRUD acepta dicts directamente
        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)

        lista_detalles = resultado["detalles"]
        total = float(resultado["total_general"])

        cambio = 0
        if tipo_pago.lower() == "efectivo":
            cambio = max(0, float(monto_recibido) - total)

        ticket_path = generar_ticket_venta_multiple(
            detalles=lista_detalles,
            total=total,
            tipo_pago=tipo_pago,
            monto_recibido=float(monto_recibido),
            cambio=cambio
        )

        ticket_name = os.path.basename(ticket_path)
        base_url = str(request.base_url).rstrip("/")
        ticket_url = f"{base_url}{router.prefix}/ticket/{ticket_name}"

        return {
            "detalles": lista_detalles,
            "total": total,
            "ticket": ticket_name,
            "ticket_url": ticket_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
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
