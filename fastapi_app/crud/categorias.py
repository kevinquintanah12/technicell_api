from sqlalchemy.orm import Session
from typing import List, Optional
from models.categoria import Categoria
from schemas.productos import CategoriaCreate, CategoriaUpdate


# 🔹 Crear categoría
def create_categoria(db: Session, payload: CategoriaCreate) -> Categoria:
    db_obj = Categoria(
        nombre=payload.nombre,
        descripcion=payload.descripcion
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# 🔹 Listar categorías
def list_categorias(db: Session, skip: int = 0, limit: int = 50) -> List[Categoria]:
    return db.query(Categoria).offset(skip).limit(limit).all()


# 🔹 Obtener categoría por ID
def get_categoria(db: Session, categoria_id: int) -> Optional[Categoria]:
    return db.get(Categoria, categoria_id)


# 🔹 Actualizar categoría
def update_categoria(db: Session, categoria_id: int, payload: CategoriaUpdate) -> Optional[Categoria]:
    obj = db.get(Categoria, categoria_id)

    if not obj:
        return None

    if payload.nombre is not None:
        obj.nombre = payload.nombre
    if payload.descripcion is not None:
        obj.descripcion = payload.descripcion

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# 🔹 Eliminar categoría
def delete_categoria(db: Session, categoria_id: int) -> bool:
    obj = db.get(Categoria, categoria_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
