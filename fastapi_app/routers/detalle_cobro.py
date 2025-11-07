from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.detalle_cobro import DetalleCobroCreate
from crud import detalle_cobro as crud_detalle

router = APIRouter(prefix="/detalle_cobro", tags=["Detalle de Cobro"])

# -----------------------------
# Crear un solo detalle de cobro
# -----------------------------
@router.post("/uno")
def crear_detalle(detalle: DetalleCobroCreate, db: Session = Depends(get_db)):
    try:
        return crud_detalle.crear_detalle_cobro(db, detalle)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Crear varios detalles de cobro
# -----------------------------
@router.post("/")
def crear_detalles(detalles: List[DetalleCobroCreate], db: Session = Depends(get_db)):
    try:
        return crud_detalle.crear_detalles_cobro(db, detalles)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Obtener todos los detalles
# -----------------------------
@router.get("/")
def obtener_detalles(db: Session = Depends(get_db)):
    try:
        return crud_detalle.obtener_detalles_cobro(db)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
