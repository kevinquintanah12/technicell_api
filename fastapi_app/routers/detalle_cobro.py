from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from database import get_db
from schemas.detalle_cobro import DetalleCobroCreate
from crud import detalle_cobro as crud_detalle
from utils.tickets import generar_ticket_venta_multiple
import os

router = APIRouter(
    prefix="/detalle_cobro",
    tags=["Detalle de Cobro"]
)

@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_detalles(detalles: List[DetalleCobroCreate], db: Session = Depends(get_db)):
    """
    Recibe SOLO body:
    [
        { "producto_id": 1, "cantidad": 2 },
        { "producto_id": 5, "cantidad": 1 }
    ]
    Crea venta múltiple + genera ticket PDF.
    """
    try:
        # resultado es: {"detalles": [...], "total_general": X}
        resultado = crud_detalle.crear_detalles_cobro(db, detalles)

        lista_detalles = resultado["detalles"]
        total = resultado["total_general"]

        # Generar ticket PDF
        ticket_path = generar_ticket_venta_multiple(
            detalles=lista_detalles,
            total=total,
            tipo_pago="Efectivo",
            monto_recibido=total,  # asumimos pago exacto
            cambio=0
        )

        return {
            "detalles": lista_detalles,
            "total": total,
            "ticket": ticket_path
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    ticket_path = os.path.join("tickets", ticket_name)
    if not os.path.exists(ticket_path):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return FileResponse(ticket_path, media_type="application/pdf", filename=ticket_name)
