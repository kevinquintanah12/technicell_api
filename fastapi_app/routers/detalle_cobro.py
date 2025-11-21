# routers/detalle_cobro.py
from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from database import get_db
from schemas.detalle_cobro import DetalleCobroCreate
from crud import detalle_cobro as crud_detalle
from utils.tickets import generar_ticket_venta_multiple

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(
    prefix="/detalle_cobro",
    tags=["Detalle de Cobro"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    """
    Acepta:
    1) Body como lista (legacy):
       [
         {"producto_id": 9, "cantidad": 1},
         {"producto_id": 10, "cantidad": 1}
       ]
    2) Body como objeto:
       {
         "detalles": [ {...}, {...} ],
         "tipo_pago": "Efectivo",
         "monto_recibido": 1000.0
       }
    También acepta query params como fallback: ?tipo_pago=Efectivo&monto_recibido=1000
    """
    try:
        # Leer body (json)
        try:
            body = await request.json()
        except Exception:
            body = None

        # Extraer detalles según formato recibido
        if isinstance(body, list):
            detalles_payload = body
            tipo_pago = request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(request.query_params.get("monto_recibido", 0.0))
        elif isinstance(body, dict):
            # Normalizamos: soportamos 'detalles' o bien una clave diferente
            detalles_payload = body.get("detalles") or body.get("detalle") or []
            tipo_pago = body.get("tipo_pago") or request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(body.get("monto_recibido", request.query_params.get("monto_recibido", 0.0) or 0.0))
            # Si detalles_payload es vacío y body itself tiene keys de detalle (legacy), intentar inferir
            if not detalles_payload and any(k in body for k in ("producto_id", "cantidad")):
                detalles_payload = [body]
        else:
            # Si no mandaron JSON o el JSON no es válido
            detalles_payload = []
            tipo_pago = request.query_params.get("tipo_pago", "Efectivo")
            monto_recibido = float(request.query_params.get("monto_recibido", 0.0))

        logger.debug("Payload recibidos: detalles=%s tipo_pago=%s monto_recibido=%s", detalles_payload, tipo_pago, monto_recibido)

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles de la venta")

        # Llamamos a CRUD para crear los detalles de cobro (asegúrate de que tu CRUD acepte la lista de dicts)
        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)

        # El CRUD debe devolver algo con lista de detalles y total_general (según tu implementación)
        lista_detalles = resultado.get("detalles", resultado.get("items", detalles_payload))
        total = float(resultado.get("total_general", resultado.get("total", sum(
            (d.get("cantidad", 1) * (d.get("precio") or d.get("precio_venta") or 0.0)) for d in lista_detalles
        ))))

        # Calcular cambio si el pago es efectivo
        monto_recibido_safe = float(monto_recibido or 0.0)
        cambio = 0.0
        if str(tipo_pago).lower() == "efectivo":
            cambio = max(0.0, monto_recibido_safe - total)

        # Generar ticket PDF usando los valores reales
        ticket_path = generar_ticket_venta_multiple(
            detalles=lista_detalles,
            total=total,
            tipo_pago=tipo_pago,
            monto_recibido=monto_recibido_safe,
            cambio=cambio
        )

        ticket_filename = os.path.basename(ticket_path)

        # Construir URL pública al ticket (asumiendo que este router está incluido con su prefix)
        base = str(request.base_url).rstrip("/")
        ticket_url = f"{base}{router.prefix}/ticket/{ticket_filename}"

        return {
            "detalles": lista_detalles,
            "total": total,
            "ticket": ticket_filename,
            "ticket_url": ticket_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando detalles de cobro")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    """
    Descarga el ticket. Acepta ticket_name = "ticket_venta_...pdf"
    """
    safe_name = os.path.basename(ticket_name)

    # Calcular la carpeta tickets absoluta (misma lógica que utils._get_tickets_dir)
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / "tickets").resolve()
    file_path = tickets_dir / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return FileResponse(str(file_path), media_type="application/pdf", filename=safe_name)
