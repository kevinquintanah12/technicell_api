from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from database import get_db
from crud import productos as crud_productos
from schemas.productos import ProductoCreate, ProductoUpdate, Producto
from models.productos import Producto as ProductoModel
from models.categoria import Categoria

# -----------------------------------------------------
# Router para Productos
# -----------------------------------------------------
router = APIRouter(
    prefix="/productos",
    tags=["productos"]
)

# -----------------------------------------------------
# Crear producto
# -----------------------------------------------------
@router.post("/", response_model=Producto, status_code=status.HTTP_201_CREATED)
def create_producto(producto: ProductoCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo producto en la base de datos.
    Incluye stock_actual y stock_minimo directamente en el producto.
    """
    db_producto = crud_productos.create_producto(db=db, producto=producto)
    return db_producto

# -----------------------------------------------------
# Listar productos con filtros y búsqueda
# -----------------------------------------------------
@router.get("/", response_model=List[Producto])
def list_productos(
    skip: int = 0,
    limit: int = 50,
    categoria_id: Optional[int] = Query(None, description="Filtrar por ID de categoría"),
    categoria_nombre: Optional[str] = Query(None, description="Filtrar por nombre de categoría"),
    q: Optional[str] = Query(None, description="Término de búsqueda (nombre, descripción o código de producto)"),
    db: Session = Depends(get_db),
):
    """
    Lista los productos con soporte para filtros:
    - Filtrar por categoría (ID o nombre)
    - Buscar texto parcial (nombre, descripción o código)
    - Paginación
    """
    query = db.query(ProductoModel).options(selectinload(ProductoModel.categoria))

    if categoria_id is not None:
        query = query.filter(ProductoModel.categoria_id == categoria_id)

    if categoria_nombre:
        query = query.join(ProductoModel.categoria).filter(Categoria.nombre.ilike(f"%{categoria_nombre}%"))

    if q:
        term = f"%{q}%"
        query = query.filter(
            or_(
                ProductoModel.nombre.ilike(term),
                ProductoModel.descripcion.ilike(term),
                ProductoModel.codigo.ilike(term)
            )
        )

    productos = query.offset(skip).limit(limit).all()
    return productos

# -----------------------------------------------------
# Obtener un producto específico
# -----------------------------------------------------
@router.get("/{producto_id}", response_model=Producto)
def get_producto(producto_id: int, db: Session = Depends(get_db)):
    """
    Obtiene un producto específico por su ID.
    Incluye la información de categoría y stock.
    """
    db_producto = crud_productos.get_producto(db, producto_id=producto_id)
    if not db_producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
    return db_producto

# -----------------------------------------------------
# Actualizar un producto (editar)
# -----------------------------------------------------
@router.put("/{producto_id}", response_model=Producto)
def update_producto(producto_id: int, payload: ProductoUpdate, db: Session = Depends(get_db)):
    """
    Actualiza un producto existente.
    Puedes modificar cualquier campo, incluyendo stock_actual y stock_minimo.
    """
    db_producto = crud_productos.update_producto(db, producto_id=producto_id, producto=payload)
    if not db_producto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado."
        )
    return db_producto

# -----------------------------------------------------
# Eliminar un producto
# -----------------------------------------------------
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

# -----------------------------------------------------
# Registrar venta de un producto y actualizar stock
# -----------------------------------------------------
@router.post("/{producto_id}/venta", status_code=status.HTTP_200_OK)
def vender_producto(producto_id: int, cantidad: int, db: Session = Depends(get_db)):
    """
    Registra la venta de un producto y actualiza su stock.
    Devuelve stock restante y alerta si está por debajo del mínimo.
    """
    try:
        resultado = crud_productos.registrar_venta(db, producto_id, cantidad)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
