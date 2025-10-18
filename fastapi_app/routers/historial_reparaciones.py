from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import SessionLocal
from crud import historial_reparaciones as crud_historial
from schemas.historial_reparaciones import HistorialReparacionCreate, HistorialReparacionOut

router = APIRouter(prefix="/reparaciones", tags=["Historial de Reparaciones"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🔹 Crear nueva reparación
@router.post("/{equipo_id}", response_model=HistorialReparacionOut, status_code=status.HTTP_201_CREATED)
def crear_reparacion(equipo_id: int, payload: HistorialReparacionCreate, db: Session = Depends(get_db)):
    return crud_historial.crear_reparacion(db, equipo_id, payload)

# 🔹 Listar historial de reparaciones por equipo
@router.get("/{equipo_id}", response_model=List[HistorialReparacionOut])
def historial_reparaciones(equipo_id: int, db: Session = Depends(get_db)):
    return crud_historial.listar_reparaciones_por_equipo(db, equipo_id)
