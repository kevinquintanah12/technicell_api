# routers/detalle_cobro.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
import os

from database import get_db
from schemas.detalle_cobro import DetalleCobroCreate
from crud import detalle_cobro as crud_detalle
from utils.tickets import generar_ticket_venta_multiple

router = APIRouter(
    prefix="/detalle_cobro",
    tags=["Detalle de Cobro"]
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_detalles(detalles: List[DetalleCobroCreate], db: Session = Depends(get_db), request: Request = None):
    """
    Recibe body:
    [
      { "producto_id": 1, "cantidad": 2 },
      { "producto_id": 5, "cantidad": 1 }
    ]
    Crea venta múltiple + genera ticket PDF y devuelve ticket (nombre) y ticket_url.
    """
    try:
        resultado = crud_detalle.crear_detalles_cobro(db, detalles)
        lista_detalles = resultado["detalles"]
        total = resultado["total_general"]

        # generar_ticket_venta_multiple devuelve ruta ABSOLUTA del archivo
        ticket_path = generar_ticket_venta_multiple(
            detalles=lista_detalles,
            total=total,
            tipo_pago="Efectivo",
            monto_recibido=total,
            cambio=0
        )

        # Normalizar: sacar solo el nombre del archivo
        ticket_filename = os.path.basename(ticket_path)

        # Construir URL pública (según tu include_router en main.py)
        ticket_url = None
        if request is not None:
            base = str(request.base_url).rstrip("/")
            # Ten en cuenta que en main.py incluyes router con prefix "/detalle-cobro"
            ticket_url = f"{base}/detalle-cobro/detalle_cobro/ticket/{ticket_filename}"

        return {
            "detalles": lista_detalles,
            "total": total,
            "ticket": ticket_filename,
            "ticket_url": ticket_url
        }

    except Exception as e:
        # Puedes cambiar a 500 si prefieres
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    """
    Descarga el ticket. Acepta ticket_name = "ticket_venta_...pdf"
    o "tickets/ticket_venta_...pdf" (lo normaliza).
    """
    safe_name = os.path.basename(ticket_name)

    # Calcular la carpeta tickets absoluta (misma lógica que utils._get_tickets_dir)
    base_dir = Path(__file__).resolve().parent.parent
    tickets_dir = (base_dir / "tickets").resolve()
    file_path = tickets_dir / safe_name

    if not file_path.exists():
        # Opcional: para debug puedes listar archivos disponibles
        # raise HTTPException(status_code=404, detail=f"Ticket no encontrado. Archivos en tickets: {list(tickets_dir.glob('*.pdf'))}")
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    return FileResponse(str(file_path), media_type="application/pdf", filename=safe_name)
