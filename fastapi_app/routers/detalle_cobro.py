# routers/detalle_cobro.py
from typing import List, Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from database import get_db
from crud import detalle_cobro as crud_detalle

# Generadores de ticket
from utils.tickets import generar_ticket_venta_multiple
from utils.ticket import generar_ticket_ingreso_reparacion

# =========================
# CONFIGURACIÓN DE TICKETS
# =========================
BASE_DIR = Path(__file__).resolve().parent.parent
TICKETS_DIR = (BASE_DIR / "tickets").resolve()
TICKETS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    """
    Crea detalles (venta o ingreso por reparación)
    y genera el ticket PDF.
    """
    try:
        try:
            body = await request.json()
        except Exception:
            body = None

        # Query params
        tipo_pago_q = request.query_params.get("tipo_pago")
        monto_recibido_q = request.query_params.get("monto_recibido")
        anticipo_q = request.query_params.get("anticipo")
        es_reparacion_q = request.query_params.get("es_reparacion")

        # Valores por defecto
        detalles_payload: List[Dict[str, Any]] = []
        tipo_pago = "Efectivo"
        monto_recibido = 0.0
        anticipo = 0.0
        es_reparacion = False

        # Body
        if isinstance(body, list):
            detalles_payload = body
            tipo_pago = tipo_pago_q or tipo_pago
            monto_recibido = float(monto_recibido_q or 0.0)
            anticipo = float(anticipo_q or 0.0)
            es_reparacion = es_reparacion_q == "true" if es_reparacion_q else False

        elif isinstance(body, dict):
            detalles_payload = body.get("detalles") or []
            tipo_pago = body.get("tipo_pago") or tipo_pago_q or tipo_pago
            monto_recibido = float(body.get("monto_recibido", monto_recibido_q or 0.0) or 0.0)
            anticipo = float(body.get("anticipo", anticipo_q or 0.0) or 0.0)
            es_reparacion = bool(
                body.get(
                    "es_reparacion",
                    (es_reparacion_q.lower() == "true") if es_reparacion_q else False
                )
            )

            if not detalles_payload and ("producto_id" in body and "cantidad" in body):
                detalles_payload = [body]

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles")

        # =========================
        # GUARDAR EN BD
        # =========================
        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)
        lista_detalles = resultado.get("detalles", [])
        total = float(resultado.get("total_general", resultado.get("total", 0.0)))

        monto_recibido_safe = float(monto_recibido or 0.0)
        anticipo_safe = float(anticipo or 0.0)
        restante = max(0.0, total - anticipo_safe)

        monto_cobrado_ahora = anticipo_safe if anticipo_safe > 0 else total
        cambio = (
            max(0.0, monto_recibido_safe - monto_cobrado_ahora)
            if tipo_pago.lower() == "efectivo"
            else 0.0
        )

        # =========================
        # GENERAR TICKET
        # =========================
        try:
            if es_reparacion:
                try:
                    ticket_path = generar_ticket_ingreso_reparacion(
                        detalles=lista_detalles,
                        total=total,
                        tipo_pago=tipo_pago,
                        monto_recibido=monto_recibido_safe,
                        cambio=cambio,
                        anticipo=anticipo_safe
                    )
                except TypeError:
                    ticket_path = generar_ticket_ingreso_reparacion(
                        detalles=lista_detalles,
                        total=total,
                        tipo_pago=tipo_pago,
                        monto_recibido=monto_recibido_safe,
                        cambio=cambio
                    )
            else:
                try:
                    ticket_path = generar_ticket_venta_multiple(
                        detalles=lista_detalles,
                        total=total,
                        tipo_pago=tipo_pago,
                        monto_recibido=monto_recibido_safe,
                        cambio=cambio,
                        anticipo=anticipo_safe
                    )
                except TypeError:
                    ticket_path = generar_ticket_venta_multiple(
                        detalles=lista_detalles,
                        total=total,
                        tipo_pago=tipo_pago,
                        monto_recibido=monto_recibido_safe,
                        cambio=cambio
                    )
        except Exception as e:
            logger.exception("Error generando ticket PDF")
            raise HTTPException(
                status_code=500,
                detail=f"Venta registrada pero error generando ticket: {e}"
            )

        # =========================
        # FORZAR /tickets
        # =========================
        original_path = Path(ticket_path)

        if not original_path.exists():
            raise HTTPException(status_code=500, detail="Ticket generado pero no encontrado")

        final_path = TICKETS_DIR / original_path.name

        if original_path.resolve() != final_path.resolve():
            try:
                original_path.replace(final_path)
            except Exception as e:
                logger.exception("Error moviendo ticket a /tickets")
                raise HTTPException(status_code=500, detail=f"No se pudo mover el ticket: {e}")

        file_size = final_path.stat().st_size
        if file_size == 0:
            raise HTTPException(status_code=500, detail="Ticket generado pero está vacío")

        ticket_name = final_path.name
        base = str(request.base_url).rstrip("/")
        ticket_url = f"{base}{router.prefix}/ticket/{ticket_name}"

        # =========================
        # RESPUESTA
        # =========================
        return {
            "detalles": lista_detalles,
            "total": total,
            "anticipo": anticipo_safe,
            "restante": restante,
            "monto_recibido": monto_recibido_safe,
            "monto_cobrado_ahora": monto_cobrado_ahora,
            "cambio": cambio,
            "es_reparacion": es_reparacion,
            "ticket": ticket_name,
            "ticket_url": ticket_url,
            "ticket_path": str(final_path.resolve()),
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
    file_path = TICKETS_DIR / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return FileResponse(
        str(file_path),
        media_type="application/pdf",
        filename=safe_name
    )
