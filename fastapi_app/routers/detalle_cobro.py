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

# Importa tus generadores de ticket (ajusta nombres/paths si difieren)
from utils.tickets import generar_ticket_venta_multiple  # ticket venta
from utils.ticket import generar_ticket_ingreso_reparacion  # ticket reparacion (si está en otro archivo)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    """
    Crea detalles (venta o ingreso por reparacion).
    Acepta:
      - Body: { "detalles": [...], "tipo_pago": "...", "monto_recibido": 0.0, "anticipo": 0.0, "es_reparacion": true }
      - O body como lista directa de detalles
      - O query params: ?tipo_pago=...&monto_recibido=...&anticipo=...&es_reparacion=true
    """
    try:
        try:
            body = await request.json()
        except Exception:
            body = None

        # Leer params por query (si vienen)
        tipo_pago_q = request.query_params.get("tipo_pago")
        monto_recibido_q = request.query_params.get("monto_recibido")
        anticipo_q = request.query_params.get("anticipo")
        es_reparacion_q = request.query_params.get("es_reparacion")

        # Values por defecto
        detalles_payload: List[Dict[str, Any]] = []
        tipo_pago: str = "Efectivo"
        monto_recibido: float = 0.0
        anticipo: float = 0.0
        es_reparacion: bool = False

        # Extraer desde body si existe
        if isinstance(body, list):
            detalles_payload = body
            if tipo_pago_q:
                tipo_pago = tipo_pago_q
            if monto_recibido_q:
                monto_recibido = float(monto_recibido_q or 0.0)
            if anticipo_q:
                anticipo = float(anticipo_q or 0.0)
            if es_reparacion_q:
                es_reparacion = es_reparacion_q.lower() == "true"

        elif isinstance(body, dict):
            detalles_payload = body.get("detalles") or []
            tipo_pago = body.get("tipo_pago") or tipo_pago_q or tipo_pago
            monto_recibido = float(body.get("monto_recibido", monto_recibido_q or 0.0) or 0.0)
            anticipo = float(body.get("anticipo", anticipo_q or 0.0) or 0.0)
            es_reparacion = bool(body.get("es_reparacion", (es_reparacion_q.lower() == "true") if es_reparacion_q else False))

            # soporte payload simple (producto_id + cantidad)
            if not detalles_payload and ("producto_id" in body and "cantidad" in body):
                detalles_payload = [body]
        else:
            # no body -> intentar leer query only (no es común)
            tipo_pago = tipo_pago_q or tipo_pago
            monto_recibido = float(monto_recibido_q or 0.0)
            anticipo = float(anticipo_q or 0.0)
            es_reparacion = (es_reparacion_q.lower() == "true") if es_reparacion_q else False

        logger.debug("detalles=%s tipo_pago=%s monto_recibido=%s anticipo=%s es_reparacion=%s",
                     detalles_payload, tipo_pago, monto_recibido, anticipo, es_reparacion)

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles")

        # Guardar en BD (tu CRUD debe devolver total y lista de detalles)
        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)
        lista_detalles = resultado.get("detalles", [])
        total = float(resultado.get("total_general", resultado.get("total", 0.0)))

        monto_recibido_safe = float(monto_recibido or 0.0)
        anticipo_safe = float(anticipo or 0.0)
        restante = max(0.0, total - anticipo_safe)

        # Determinar monto que se cobró ahora (anticipo si > 0, si no el total)
        monto_cobrado_ahora = anticipo_safe if anticipo_safe > 0 else total

        # Calcular cambio solo si pago efectivo y monto recibido refiere a lo que se entregó ahora
        cambio = max(0.0, monto_recibido_safe - monto_cobrado_ahora) if tipo_pago.lower() == "efectivo" else 0.0

        # Generar ticket: intentamos pasar 'anticipo' si la función lo acepta; si no, fallback
        ticket_path: Optional[str] = None
        try:
            if es_reparacion:
                # intentar pasar anticipo
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
                    # firma sin anticipo
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
            # la venta ya está registrada, devolvemos error de ticket
            raise HTTPException(status_code=500, detail=f"Venta/ingreso registrado pero error generando ticket: {e}")

        # Validar archivo generado
        file_path = Path(ticket_path)
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Ticket generado pero archivo no encontrado")
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise HTTPException(status_code=500, detail="Ticket generado pero el archivo está vacío")

        ticket_name = os.path.basename(ticket_path)
        base = str(request.base_url).rstrip("/")  # e.g. http://host:8000
        ticket_url = f"{base}{router.prefix}/ticket/{ticket_name}"

        # Respuesta
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
