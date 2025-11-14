from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db

# Importar correctamente desde crud.categorias
from crud import categorias as crud_categorias

# Esquemas correctos desde schemas.productos
from schemas.productos import Categoria, CategoriaCreate, CategoriaUpdate

router = APIRouter(
    prefix="/categorias",
    tags=["categorias"]
)

@router.post("/", response_model=Categoria, status_code=status.HTTP_201_CREATED)
def create_categoria(categoria: CategoriaCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva categoría.
    """
    return crud_categorias.create_categoria(db=db, payload=categoria)

@router.get("/", response_model=List[Categoria])
def list_categorias(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Obtiene una lista de todas las categorías.
    """
    return crud_categorias.list_categorias(db, skip=skip, limit=limit)

@router.get("/{categoria_id}", response_model=Categoria)
def get_categoria(categoria_id: int, db: Session = Depends(get_db)):
    """
    Obtiene una categoría por su ID.
    """
    db_categoria = crud_categorias.get_categoria(db, categoria_id=categoria_id)
    
    if not db_categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada."
        )
    return db_categoria

@router.put("/{categoria_id}", response_model=Categoria)
def update_categoria(categoria_id: int, payload: CategoriaUpdate, db: Session = Depends(get_db)):
    """
    Actualiza una categoría existente.
    """
    db_categoria = crud_categorias.update_categoria(
        db=db,
        categoria_id=categoria_id,
        payload=payload
    )

    if not db_categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoría no encontrada."
        )
    
    return db_categoria
