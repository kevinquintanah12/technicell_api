from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from database import get_db
from crud import ingreso_reparacion as crud_ingreso
from utils.ticket import generar_ticket_ingreso_reparacion

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="/ingreso_reparacion", tags=["Ingreso Reparacion"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear_ingreso_reparacion(request: Request, db: Session = Depends(get_db)):
    """
    Crea un ingreso por reparación y genera su ticket PDF.
    Body esperado (ejemplo):
    {
      "cliente_nombre": "Juan Pérez",
      "cliente_id": 1,                    # opcional
      "equipo": "iPhone 13",
      "modelo": "A2633",
      "imei": "123456789012345",
      "falla_reportada": "No enciende",
      "observaciones": "Se apaga solo",
      "anticipo": 150.0,
      "total_estimado": 600.0,
      "tipo_pago": "Efectivo",
      "monto_recibido": 150.0
    }
    """
    try:
        try:
            body = await request.json()
        except Exception:
            body = None

        if not body or not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Se espera un JSON con los datos del ingreso")

        # Campos relevantes
        cliente_nombre = body.get("cliente_nombre") or body.get("cliente")  # soporte alias
        equipo = body.get("equipo")
        falla_reportada = body.get("falla_reportada") or body.get("falla")
        modelo = body.get("modelo")
        imei = body.get("imei")
        observaciones = body.get("observaciones")
        cliente_id = body.get("cliente_id")
        anticipo = float(body.get("anticipo", 0.0) or 0.0)
        total_estimado = float(body.get("total_estimado", 0.0) or 0.0)

        tipo_pago = body.get("tipo_pago", "Efectivo")
        monto_recibido = float(body.get("monto_recibido", 0.0) or 0.0)

        # Validaciones mínimas
        if not cliente_nombre or not equipo or not falla_reportada:
            raise HTTPException(
                status_code=400,
                detail="Faltan campos obligatorios: 'cliente_nombre', 'equipo' o 'falla_reportada'"
            )

        ingreso_payload: Dict[str, Any] = {
            "cliente_id": cliente_id,
            "cliente_nombre": cliente_nombre,
            "equipo": equipo,
            "modelo": modelo,
            "imei": imei,
            "falla_reportada": falla_reportada,
            "observaciones": observaciones,
            "anticipo": anticipo,
            "total_estimado": total_estimado,
        }

        logger.debug("Creando ingreso_reparacion: %s", ingreso_payload)

        # Guardar en BD (tu CRUD debe aceptar dict o adaptarlo)
        ingreso = crud_ingreso.crear_ingreso(db, ingreso_payload)
        if ingreso is None:
            raise HTTPException(status_code=500, detail="No se pudo crear el ingreso en la base de datos")

        # Determinar montos a reportar
        # Preferir total_final si el CRUD lo llenó, sino total_estimado
        total = float(getattr(ingreso, "total_final", None) or getattr(ingreso, "total_estimado", None) or total_estimado or 0.0)
        anticipo_safe = float(anticipo or 0.0)
        monto_recibido_safe = float(monto_recibido or 0.0)

        monto_cobrado_ahora = anticipo_safe if anticipo_safe > 0 else total
        cambio = max(0.0, monto_recibido_safe - monto_cobrado_ahora) if tipo_pago.lower() == "efectivo" else 0.0

        # Preparar dict que recibirá el generador de ticket
        # si ingreso es objeto ORM lo convertimos a dict simple
        try:
            ingreso_dict = ingreso.__dict__.copy()
            # limpiar claves internas si existen
            ingreso_dict.pop("_sa_instance_state", None)
        except Exception:
            ingreso_dict = dict(ingreso) if isinstance(ingreso, dict) else {"id": getattr(ingreso, "id", None)}

        # Generar ticket PDF (intento con anticipo, si no, sin anticipo)
        ticket_path: Optional[str] = None
        try:
            try:
                ticket_path = generar_ticket_ingreso_reparacion(
                    ingreso=ingreso_dict,
                    tipo_pago=tipo_pago,
                    monto_recibido=monto_recibido_safe,
                    cambio=cambio,
                    anticipo=anticipo_safe,
                )
            except TypeError:
                # Firma alternativa sin 'anticipo'
                ticket_path = generar_ticket_ingreso_reparacion(
                    ingreso=ingreso_dict,
                    tipo_pago=tipo_pago,
                    monto_recibido=monto_recibido_safe,
                    cambio=cambio,
                )
        except Exception as e:
            logger.exception("Error generando ticket de ingreso de reparación")
            # El ingreso ya fue registrado; devolvemos error indicando el ticket
            raise HTTPException(status_code=500, detail=f"Ingreso registrado pero error generando ticket: {e}")

        # Validar archivo generado
        file_path = Path(ticket_path)
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Ticket generado pero archivo no encontrado")
        file_size = file_path.stat().st_size
        if file_size == 0:
            raise HTTPException(status_code=500, detail="Ticket generado pero el archivo está vacío")

        ticket_name = os.path.basename(ticket_path)
        base = str(request.base_url).rstrip("/")  # e.g. http://host:8000
        ticket_url = f"/ingreso/ingreso_reparacion/ticket/{ticket_name}"


        # Respuesta
        return {
            "ingreso": ingreso_dict,
            "id": getattr(ingreso, "id", None),
            "total": total,
            "anticipo": anticipo_safe,
            "monto_recibido": monto_recibido_safe,
            "monto_cobrado_ahora": monto_cobrado_ahora,
            "cambio": cambio,
            "ticket": ticket_name,
            "ticket_url": ticket_url,
            "ticket_path": str(file_path.resolve()),
            "ticket_size_bytes": file_size,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creando ingreso de reparación")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ingreso_id}")
def obtener_ingreso(ingreso_id: int, db: Session = Depends(get_db)):
    ingreso = crud_ingreso.obtener_ingreso(db, ingreso_id)
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    # si es ORM, devolverlo como dict ORMs deben estar permitidos por Pydantic en la app; aquí devolvemos raw
    try:
        ingreso_dict = ingreso.__dict__.copy()
        ingreso_dict.pop("_sa_instance_state", None)
    except Exception:
        ingreso_dict = dict(ingreso) if isinstance(ingreso, dict) else {"id": ingreso_id}
    return ingreso_dict


@router.put("/{ingreso_id}")
def actualizar_ingreso(ingreso_id: int, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Actualiza campos del ingreso. payload puede contener: estado, total_final, observaciones, anticipo, etc.
    """
    ingreso_actualizado = crud_ingreso.actualizar_ingreso(db, ingreso_id, payload)
    if not ingreso_actualizado:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado o no se pudo actualizar")
    try:
        ingreso_dict = ingreso_actualizado.__dict__.copy()
        ingreso_dict.pop("_sa_instance_state", None)
    except Exception:
        ingreso_dict = dict(ingreso_actualizado) if isinstance(ingreso_actualizado, dict) else {"id": ingreso_id}
    return ingreso_dict


@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    safe_name = os.path.basename(ticket_name)
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / "tickets").resolve()
    file_path = tickets_dir / safe_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return FileResponse(str(file_path), media_type="application/pdf", filename=safe_name)
