# routers/estados_equipos.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import SessionLocal
from crud import estados_equipo as crud_estados
from schemas.estado_equipo import EstadoEquipoCreate, EstadoEquipoOut

router = APIRouter(prefix="/estados", tags=["Estados de Equipos"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 🔹 Crear un nuevo estado
@router.post("/{equipo_id}", response_model=EstadoEquipoOut, status_code=status.HTTP_201_CREATED)
def crear_estado(equipo_id: int, payload: EstadoEquipoCreate, db: Session = Depends(get_db)):
    try:
        return crud_estados.crear_estado_equipo(db, equipo_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 🔹 Listar historial de un equipo
@router.get("/{equipo_id}", response_model=List[EstadoEquipoOut])
def historial_estados(equipo_id: int, db: Session = Depends(get_db)):
    return crud_estados.listar_estados_equipo(db, equipo_id)
