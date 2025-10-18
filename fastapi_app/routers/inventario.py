from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from crud import productos as crud_productos
from schemas.productos import Inventario, InventarioCreate, InventarioUpdate

router = APIRouter(
    prefix="/inventario",
    tags=["inventario"]
)

@router.post("/", response_model=Inventario, status_code=status.HTTP_201_CREATED)
def create_inventario(payload: InventarioCreate, db: Session = Depends(get_db)):
    """
    Crea un registro de inventario para un producto.
    """
    return crud_productos.create_inventario_for_producto(db=db, producto_id=payload.producto_id, stock_inicial=payload.stock_actual)

@router.get("/{producto_id}", response_model=Inventario)
def get_inventario(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtiene el registro de inventario para un producto por su ID.
    """
    db_inventario = crud_productos.get_inventario(db, producto_id=producto_id)
    if not db_inventario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de inventario no encontrado para este producto."
        )
    return db_inventario

@router.put("/{producto_id}", response_model=Inventario)
def update_inventario(producto_id: int, payload: InventarioUpdate, db: Session = Depends(get_db)):
    """
    Actualiza el stock o stock mínimo de un producto.
    """
    db_inventario = crud_productos.update_inventario(db, producto_id=producto_id, payload=payload)
    if not db_inventario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de inventario no encontrado."
        )
    return db_inventario