from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

# Importamos los modelos y esquemas necesarios
from models.categoria import Categoria
from models.productos import Producto
from models.inventario import Inventario
from schemas.productos import (
    CategoriaCreate, CategoriaUpdate,
    ProductoCreate, ProductoUpdate,
    InventarioCreate, InventarioUpdate
)

# --- OPERACIONES CRUD PARA CATEGORIA ---
def create_categoria(db: Session, payload: CategoriaCreate) -> Categoria:
    db_obj = Categoria(**payload.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_categoria(db: Session, categoria_id: int) -> Optional[Categoria]:
    return db.get(Categoria, categoria_id)

def list_categorias(db: Session, skip: int = 0, limit: int = 50) -> List[Categoria]:
    return list(db.execute(select(Categoria).offset(skip).limit(limit)).scalars())

# --- OPERACIONES CRUD PARA PRODUCTO ---
def create_producto(db: Session, payload: ProductoCreate) -> Producto:
    db_obj = Producto(**payload.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_producto(db: Session, producto_id: int) -> Optional[Producto]:
    return db.get(Producto, producto_id)

def list_productos(db: Session, skip: int = 0, limit: int = 50, categoria_id: Optional[int] = None) -> List[Producto]:
    stmt = select(Producto)
    if categoria_id is not None:
        stmt = stmt.where(Producto.categoria_id == categoria_id)
    return list(db.execute(stmt.offset(skip).limit(limit)).scalars())

def update_producto(db: Session, producto_id: int, payload: ProductoUpdate) -> Optional[Producto]:
    db_obj = db.get(Producto, producto_id)
    if not db_obj:
        return None
    
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_producto(db: Session, producto_id: int) -> bool:
    db_obj = db.get(Producto, producto_id)
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True

# --- OPERACIONES CRUD PARA INVENTARIO ---
def create_inventario_for_producto(db: Session, producto_id: int, stock_inicial: int = 0) -> Inventario:
    # Verificamos si el inventario ya existe para este producto
    existing_inventory = db.get(Inventario, producto_id)
    if existing_inventory:
        raise ValueError("Inventario para este producto ya existe.")
    
    db_obj = Inventario(producto_id=producto_id, stock_actual=stock_inicial)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_inventario(db: Session, producto_id: int) -> Optional[Inventario]:
    return db.query(Inventario).filter(Inventario.producto_id == producto_id).first()

def update_inventario(db: Session, producto_id: int, payload: InventarioUpdate) -> Optional[Inventario]:
    db_obj = get_inventario(db, producto_id)
    if not db_obj:
        return None
    
    # Solo actualizamos el stock, no la fecha
    if payload.stock_actual is not None:
        db_obj.stock_actual = payload.stock_actual
        db_obj.fecha_ultima_actualizacion = datetime.utcnow() # Actualizamos el timestamp
    if payload.stock_minimo is not None:
        db_obj.stock_minimo = payload.stock_minimo
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj