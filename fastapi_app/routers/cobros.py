from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from crud import cobros as crud_cobros
from schemas.cobros import CobroCreate, CobroUpdate, CobroOut

router = APIRouter(prefix="/cobros", tags=["Cobros"])

# --------------------------------
# Crear cobro (sin generar ticket)
# --------------------------------
@router.post("/", response_model=CobroOut)
def crear_cobro(cobro: CobroCreate, db: Session = Depends(get_db)):
    try:
        nuevo_cobro = crud_cobros.create_cobro(db, cobro)
        return nuevo_cobro
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Listar cobros
# -----------------------------
@router.get("/", response_model=list[CobroOut])
def listar_cobros(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_cobros.get_cobros(db, skip, limit)


# ---------------------------------------
# Actualizar cobro (sin regenerar ticket)
# ---------------------------------------
@router.put("/{cobro_id}", response_model=CobroOut)
def actualizar_cobro(cobro_id: int, cobro: CobroUpdate, db: Session = Depends(get_db)):
    updated = crud_cobros.update_cobro(db, cobro_id, cobro)
    if not updated:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    return updated
