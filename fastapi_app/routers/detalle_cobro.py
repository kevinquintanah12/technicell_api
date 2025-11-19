# routers/detalle_cobro.py
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


# -----------------------------------------------------
# CREAR VARIOS DETALLES (SOLO BODY) Y GENERAR TICKET
# -----------------------------------------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_detalles(
    detalles: List[DetalleCobroCreate],
    db: Session = Depends(get_db)
):
    """
    Crea varios detalles de cobro usando solo el body.
    Calcula total, cambio (igual a total), y genera ticket PDF.
    """

    try:
        # Crear detalles desde CRUD
        resultado = crud_detalle.crear_detalles_cobro(db, detalles)

        # Extraer total desde el CRUD
        total = resultado.get("total_general", 0)

        # Como no recibimos pago, monto recibido = total
        monto_recibido = total  
        cambio = 0  

        # Generar ticket PDF
        ticket_path = generar_ticket_venta_multiple(
            detalles=resultado["detalles"],
            total=total,
            tipo_pago="Efectivo",
            monto_recibido=monto_recibido,
            cambio=cambio
        )

        return {
            "detalles": resultado["detalles"],
            "total": total,
            "tipo_pago": "Efectivo",
            "monto_recibido": monto_recibido,
            "cambio": cambio,
            "ticket": ticket_path
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# -----------------------------------------------------
# CREAR UN DETALLE (OPCIONAL)
# -----------------------------------------------------
@router.post("/uno", status_code=status.HTTP_201_CREATED)
def crear_detalle(detalle: DetalleCobroCreate, db: Session = Depends(get_db)):
    try:
        return crud_detalle.crear_detalle_cobro(db, detalle)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# -----------------------------------------------------
# OBTENER TODOS LOS DETALLES
# -----------------------------------------------------
@router.get("/", status_code=status.HTTP_200_OK)
def obtener_detalles(db: Session = Depends(get_db)):
    try:
        return crud_detalle.obtener_detalles_cobro(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# -----------------------------------------------------
# OBTENER VENTAS AGRUPADAS POR PRODUCTO
# -----------------------------------------------------
@router.get("/ventas-por-producto", status_code=status.HTTP_200_OK)
def obtener_ventas_por_producto(db: Session = Depends(get_db)):
    try:
        return crud_detalle.obtener_cantidades_vendidas_por_producto(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# -----------------------------------------------------
# DESCARGAR TICKET
# -----------------------------------------------------
@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    ticket_path = os.path.join("tickets", ticket_name)
    if not os.path.exists(ticket_path):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return FileResponse(ticket_path, media_type="application/pdf", filename=ticket_name)
