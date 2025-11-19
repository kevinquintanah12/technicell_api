# routers/detalle_cobro.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from database import get_db
from schemas.detalle_cobro import DetalleCobroCreate
from crud import detalle_cobro as crud_detalle
from utils.tickets import generar_ticket_venta_multiple, generar_ticket_profesional
from datetime import datetime
import os

router = APIRouter(
    prefix="/detalle_cobro",
    tags=["Detalle de Cobro"]
)


@router.post("/uno", status_code=status.HTTP_201_CREATED)
def crear_detalle(detalle: DetalleCobroCreate, db: Session = Depends(get_db)):
    """
    Crea un solo detalle de cobro (venta de un producto)
    y descuenta el stock automáticamente.
    """
    try:
        return crud_detalle.crear_detalle_cobro(db, detalle)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_detalles(
    detalles: List[DetalleCobroCreate],
    db: Session = Depends(get_db),
    tipo_pago: str = Query("Efectivo", description="Tipo de pago, p.ej. Efectivo"),
    monto_recibido: float = Query(0.0, description="Monto recibido para calcular cambio")
):
    """
    Crea varios detalles de cobro (venta múltiple), descuenta stock y genera ticket PDF.
    Recibe lista de DetalleCobroCreate en el body; recibe tipo_pago y monto_recibido como query params opcionales.
    """
    try:
        # crear detalles usando tu CRUD (devuelve lista de detalles creados)
        resultado = crud_detalle.crear_detalles_cobro(db, detalles)

        # Calcular total: intentar sumar subtotales; si no existen, calcular desde cantidad * precio_unitario
        total = 0.0
        # resultado puede ser lista de dicts o de objetos
        for item in resultado:
            subtotal = None
            if isinstance(item, dict):
                subtotal = item.get("subtotal")
                if subtotal is None:
                    # intentar calcular
                    cantidad = item.get("cantidad", 1)
                    precio_unit = item.get("precio_unitario") or item.get("precio")
                    try:
                        subtotal = float(cantidad) * float(precio_unit)
                    except Exception:
                        subtotal = 0.0
            else:
                subtotal = getattr(item, "subtotal", None)
                if subtotal is None:
                    cantidad = getattr(item, "cantidad", 1)
                    precio_unit = getattr(item, "precio_unitario", None) or getattr(item, "precio", 0.0)
                    try:
                        subtotal = float(cantidad) * float(precio_unit)
                    except Exception:
                        subtotal = 0.0

            try:
                total += float(subtotal or 0.0)
            except Exception:
                total += 0.0

        monto_recibido_val = float(monto_recibido or 0.0)
        cambio = max(0.0, monto_recibido_val - total)

        # Generar ticket PDF
        ticket_path = generar_ticket_venta_multiple(
            detalles=resultado,
            total=total,
            tipo_pago=tipo_pago,
            monto_recibido=monto_recibido_val,
            cambio=cambio
        )

        # Respuesta: devolvemos los detalles y la ruta del ticket (igual que en tu endpoint de cobros)
        return {
            "detalles": resultado,
            "total": total,
            "tipo_pago": tipo_pago,
            "monto_recibido": monto_recibido_val,
            "cambio": cambio,
            "ticket": ticket_path
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", status_code=status.HTTP_200_OK)
def obtener_detalles(db: Session = Depends(get_db)):
    """
    Devuelve todos los registros de detalle de cobro (ventas individuales).
    """
    try:
        return crud_detalle.obtener_detalles_cobro(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ventas-por-producto", status_code=status.HTTP_200_OK)
def obtener_ventas_por_producto(db: Session = Depends(get_db)):
    """
    Devuelve la cantidad total vendida y el monto total agrupado por producto.
    """
    try:
        return crud_detalle.obtener_cantidades_vendidas_por_producto(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Endpoint para descargar ticket por nombre de archivo
@router.get("/ticket/{ticket_name}")
def descargar_ticket(ticket_name: str):
    ticket_path = os.path.join("tickets", ticket_name)
    if not os.path.exists(ticket_path):
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return FileResponse(ticket_path, media_type="application/pdf", filename=ticket_name)
