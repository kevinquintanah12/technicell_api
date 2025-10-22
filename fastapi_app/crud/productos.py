from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
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
    """
    Devuelve un producto por su ID, incluyendo su categoría.
    """
    stmt = select(Producto).options(selectinload(Producto.categoria)).where(Producto.id == producto_id)
    return db.execute(stmt).scalars().first()


def list_productos(db: Session, skip: int = 0, limit: int = 50, categoria_id: Optional[int] = None) -> List[dict]:
    """
    Devuelve una lista de productos incluyendo su categoría (nombre).
    """
    stmt = select(Producto).options(selectinload(Producto.categoria))
    if categoria_id is not None:
        stmt = stmt.where(Producto.categoria_id == categoria_id)

    productos = db.execute(stmt.offset(skip).limit(limit)).scalars().all()

    # Convertimos el resultado a una lista de diccionarios incluyendo el nombre de la categoría
    resultado = []
    for p in productos:
        resultado.append({
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "codigo": p.codigo,
            "precio_venta": p.precio_venta,
            "activo": p.activo,
            "categoria_id": p.categoria_id,
            "categoria_nombre": p.categoria.nombre if p.categoria else None
        })
    return resultado


def update_producto(db: Session, producto_id: int, payload: ProductoUpdate) -> Optional[Producto]:
    """
    Actualiza los datos de un producto existente.
    """
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
    """
    Elimina un producto por su ID.
    """
    db_obj = db.get(Producto, producto_id)
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True


# --- OPERACIONES CRUD PARA INVENTARIO ---
def create_inventario_for_producto(db: Session, producto_id: int, stock_inicial: int = 0) -> Inventario:
    """
    Crea el inventario de un producto específico si aún no existe.
    """
    existing_inventory = db.get(Inventario, producto_id)
    if existing_inventory:
        raise ValueError("Inventario para este producto ya existe.")
    
    db_obj = Inventario(producto_id=producto_id, stock_actual=stock_inicial)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_inventario(db: Session, producto_id: int) -> Optional[Inventario]:
    """
    Obtiene el inventario de un producto.
    """
    return db.query(Inventario).filter(Inventario.producto_id == producto_id).first()


def update_inventario(db: Session, producto_id: int, payload: InventarioUpdate) -> Optional[Inventario]:
    """
    Actualiza el inventario (stock) de un producto.
    """
    db_obj = get_inventario(db, producto_id)
    if not db_obj:
        return None
    
   
