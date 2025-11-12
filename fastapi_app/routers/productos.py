from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from crud import crud_productos

router = APIRouter()

@router.post("/ventas/{producto_id}")
def vender_producto(producto_id: int, cantidad: int, db: Session = Depends(get_db)):
    try:
        resultado = crud_productos.registrar_venta(db, producto_id, cantidad)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
