# routers/detalle_cobro.py
from typing import List, Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from pathlib import Path
import os
import logging

from database import get_db
from crud import detalle_cobro as crud_detalle
from utils.tickets import generar_ticket_venta_multiple

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])


# ---------------------- Pydantic (opcional, útil para documentación) ----------------------
class DetalleCobroBase(BaseModel):
    producto_id: int
    cantidad: int


class DetalleCobroCreate(DetalleCobroBase):
    pass


class DetalleCobro(DetalleCobroBase):
    id: int
    subtotal: float

    class Config:
        orm_mode = True


# ---------------------- Endpoints ----------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_detalles(request: Request, db: Session = Depends(get_db)):
    """
    Crea los detalles de cobro (venta). Acepta body como lista o dict con "detalles".
    Opcionales (body o query params):
      - tipo_pago (string) (default "Efectivo")
      - monto_recibido (float) (monto que llegó físicamente)
      - anticipo (float) (cantidad de anticipo cobrada)
    Responde con info de la venta y el ticket generado (nombre, url, path, size).
    """
    try:
        # leer body (puede ser json o estar vacío)
        try:
            body = await request.json()
        except Exception:
            body = None

        # Determinar detalles, tipo_pago, monto_recibido y anticipo
        detalles_payload: List[Dict[str, Any]] = []
        tipo_pago = request.query_params.get("tipo_pago", "Efectivo")
        monto_recibido = float(request.query_params.get("monto_recibido", 0.0) or 0.0)
        anticipo = float(request.query_params.get("anticipo", 0.0) or 0.0)

        if isinstance(body, list):
            detalles_payload = body
            # permitir override en body
            tipo_pago = body[0].get("tipo_pago", tipo_pago) if body else tipo_pago
            # si el arreglo no trae monto_recibido / anticipo, mantener query params
        elif isinstance(body, dict):
            detalles_payload = body.get("detalles") or []
            tipo_pago = body.get("tipo_pago", tipo_pago)
            monto_recibido = float(body.get("monto_recibido", monto_recibido or 0.0) or 0.0)
            anticipo = float(body.get("anticipo", anticipo or 0.0) or 0.0)
            # soporte para payload simple (producto_id + cantidad)
            if not detalles_payload and ("producto_id" in body and "cantidad" in body):
                detalles_payload = [body]
        else:
            raise HTTPException(status_code=400, detail="Formato de body inválido")

        logger.debug("Request recibida: detalles=%s tipo_pago=%s monto_recibido=%s anticipo=%s",
                     detalles_payload, tipo_pago, monto_recibido, anticipo)

        if not detalles_payload:
            raise HTTPException(status_code=400, detail="No se enviaron detalles")

        # Guardar en BD (implementación en crud.detalle_cobro)
        resultado = crud_detalle.crear_detalles_cobro(db, detalles_payload)

        lista_detalles = resultado.get("detalles", [])
        total = float(resultado.get("total_general", resultado.get("total", 0.0)))

        # Validar valores numéricos
        monto_recibido_safe = float(monto_recibido or 0.0)
        anticipo_safe = float(anticipo or 0.0)
        restante = max(0.0, total - anticipo_safe)

        # Calcular cambio solo si el pago en efectivo aplica al monto recibido (puede ser anticipo o total)
        cambio = 0.0
        # decidir monto esperado para comparar con monto_recibido: si anticipo > 0 y monto_recibido se refiere al anticipo,
        # normalmente monto_recibido contiene lo que se entregó ahora; asumimos que monto_recibido es lo recibido ahora.
        monto_a_cobrar_ahora = (anticipo_safe if anticipo_safe > 0 else total)
        if str(tipo_pago).lower() == "efectivo":
            cambio = max(0.0, monto_recibido_safe - monto_a_cobrar_ahora)

        # Intentar generar ticket (si el generador acepta 'anticipo' lo incluimos; si no, lo llamamos sin ese parámetro)
        ticket_path = None
        try:
            # Primero intentamos pasar anticipo como kwarg (si la función fue adaptada)
            ticket_path = generar_ticket_venta_multiple(
                detalles=lista_detalles,
                total=total,
                tipo_pago=tipo_pago,
                monto_recibido=monto_recibido_safe,
                cambio=cambio,
                anticipo=anticipo_safe,  # opcional para la función
            )
        except TypeError:
            # La función no acepta 'anticipo' -> llamamos sin él
            logger.debug("generar_ticket_venta_multiple no acepta 'anticipo' - llamando sin ese argumento")
            try:
                ticket_path = generar_ticket_venta_multiple(
                    detalles=lista_detalles,
                    total=total,
                    tipo_pago=tipo_pago,
                    monto_recibido=monto_recibido_safe,
                    cambio=cambio,
                )
            except Exception as e:
                logger.exception("Fallo al generar ticket PDF (segunda llamada sin anticipo)")
                raise HTTPException(status_code=500, detail=f"Venta registrada pero error generando ticket: {e}")
        except Exception as e:
            logger.exception("Fallo al generar ticket PDF")
            raise HTTPException(status_code=500, detail=f"Venta registrada pero error generando ticket: {e}")

        # Validar archivo generado
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

        ticket_name = os.path.basename(ticket_path)
        base = str(request.base_url).rstrip("/")  # ej. http://host:8000
        # Construir URL correcta: base + router.prefix + '/ticket/{name}'
        ticket_url = f"{base}{router.prefix}/ticket/{ticket_name}"

        # Respuesta: incluye anticipo y restante
        return {
            "detalles": lista_detalles,
            "total": total,
            "anticipo": anticipo_safe,
            "restante": restante,
            "monto_recibido": monto_recibido_safe,
            "monto_a_cobrar_ahora": monto_a_cobrar_ahora,
            "cambio": cambio,
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


@router.get("/ticket/{ticket_name}", response_class=FileResponse)
def descargar_ticket(ticket_name: str):
    """
    Devuelve el PDF del ticket por su nombre (bajo carpeta ./tickets).
    """
    safe_name = os.path.basename(ticket_name)
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / "tickets").resolve()
    file_path = tickets_dir / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return FileResponse(str(file_path), media_type="application/pdf", filename=safe_name)
