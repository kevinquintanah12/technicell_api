from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from typing import List
from schemas.detalle_cobro import DetalleCobroCreate, DetalleCobroRead, DetalleCobroUpdate
from crud import detalle_cobro as crud_detalle
from crud import cobros as crud_cobro  # ✅ Para actualizar monto total del cobro

router = APIRouter(prefix="/detalles-cobro", tags=["Detalles de Cobro"])

# ---------------------------------------------------
# Crear detalle de cobro
# ---------------------------------------------------
@router.post("/", response_model=DetalleCobroRead)
def crear_detalle_cobro(detalle: DetalleCobroCreate, db: Session = Depends(get_db)):
    db_detalle = crud_detalle.create_detalle_cobro(db=db, detalle=detalle)
    if not db_detalle:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # ✅ Actualizar automáticamente el monto total y saldo del cobro
    crud_cobro.actualizar_montos_cobro(db, detalle.cobro_id)

    return db_detalle


# ---------------------------------------------------
# Listar todos los detalles
# ---------------------------------------------------
@router.get("/", response_model=List[DetalleCobroRead])
def listar_detalles_cobro(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_detalle.get_detalles_cobro(db=db, skip=skip, limit=limit)


# ---------------------------------------------------
# Obtener un detalle por ID
# ---------------------------------------------------
@router.get("/{detalle_id}", response_model=DetalleCobroRead)
def obtener_detalle_cobro(detalle_id: int, db: Session = Depends(get_db)):
    db_detalle = crud_detalle.get_detalle_cobro_by_id(db=db, detalle_id=detalle_id)
    if not db_detalle:
        raise HTTPException(status_code=404, detail="Detalle de cobro no encontrado")
    return db_detalle


# ---------------------------------------------------
# Actualizar detalle de cobro
# ---------------------------------------------------
@router.put("/{detalle_id}", response_model=DetalleCobroRead)
def actualizar_detalle_cobro(detalle_id: int, detalle: DetalleCobroUpdate, db: Session = Depends(get_db)):
    db_detalle = crud_detalle.update_detalle_cobro(db=db, detalle_id=detalle_id, detalle=detalle)
    if not db_detalle:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")

    # ✅ Actualizar los totales del cobro relacionado
    crud_cobro.actualizar_montos_cobro(db, db_detalle.cobro_id)

    return db_detalle


# ---------------------------------------------------
# Eliminar detalle de cobro
# ---------------------------------------------------
@router.delete("/{detalle_id}")
def eliminar_detalle_cobro(detalle_id: int, db: Session = Depends(get_db)):
    db_detalle = crud_detalle.get_detalle_cobro_by_id(db, detalle_id)
    if not db_detalle:
        raise HTTPException(status_code=404, detail="Detalle de cobro no encontrado")

    crud_detalle.delete_detalle_cobro(db=db, detalle_id=detalle_id)

    # ✅ Actualizar montos del cobro después de eliminar el detalle
    crud_cobro.actualizar_montos_cobro(db, db_detalle.cobro_id)

    return {"ok": True, "message": "Detalle eliminado correctamente"}
