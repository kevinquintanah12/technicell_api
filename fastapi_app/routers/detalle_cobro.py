from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.detalle_cobro import DetalleCobroCreate
from crud import detalle_cobro as crud_detalle

# ----------------------------------
# Router para Detalle de Cobro
# ----------------------------------
router = APIRouter(
    prefix="/detalle_cobro",
    tags=["Detalle de Cobro"]
)


# ----------------------------------
# Crear un solo detalle de cobro
# ----------------------------------
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


# ----------------------------------
# Crear varios detalles de cobro
# ----------------------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_detalles(detalles: List[DetalleCobroCreate], db: Session = Depends(get_db)):
    """
    Crea varios detalles de cobro (venta múltiple)
    y descuenta el stock de todos los productos involucrados.
    """
    try:
        return crud_detalle.crear_detalles_cobro(db, detalles)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------
# Obtener todos los detalles de cobro
# ----------------------------------
@router.get("/", status_code=status.HTTP_200_OK)
def obtener_detalles(db: Session = Depends(get_db)):
    """
    Devuelve todos los registros de detalle de cobro (ventas individuales).
    """
    try:
        return crud_detalle.obtener_detalles_cobro(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------
# Obtener resumen de ventas por producto
# ----------------------------------
@router.get("/ventas-por-producto", status_code=status.HTTP_200_OK)
def obtener_ventas_por_producto(db: Session = Depends(get_db)):
    """
    Devuelve la cantidad total vendida y el monto total
    agrupado por producto.
    """
    try:
        return crud_detalle.obtener_cantidades_vendidas_por_producto(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
