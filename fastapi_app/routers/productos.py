from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from crud import productos as crud_productos
from schemas.productos import ProductoCreate, ProductoUpdate, Producto

# Creamos una instancia de APIRouter
router = APIRouter(
    prefix="/productos",
    tags=["productos"]
)

@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED)
def create_producto(producto: ProductoCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo producto en la base de datos.
    """
    db_producto = crud_productos.create_producto(db=db, payload=producto)
    return db_producto

@router.get("/", response_model=List[Producto])
def list_productos(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Obtiene una lista de todos los productos.
    """
    productos = crud_productos.list_productos(db, skip=skip, limit=limit)
    return productos

@router.get("/{producto_id}", response_model=Producto)
def get_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un producto por su ID.
    """
    db_producto = crud_productos.get_producto(db, producto_id=producto_id)
    if not db_producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
    return db_producto

@router.put("/{producto_id}", response_model=Producto)
def update_producto(producto_id: int, payload: ProductoUpdate, db: Session = Depends(get_db)):
    """
    Actualiza un producto existente por su ID.
    """
    db_producto = crud_productos.update_producto(db, producto_id=producto_id, payload=payload)
    if not db_producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
    return db_producto

@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Elimina un producto por su ID.
    """
    success = crud_productos.delete_producto(db, producto_id=producto_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
    return {"message": "Producto eliminado exitosamente."}