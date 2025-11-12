from typing import Optional, List
from pydantic import BaseModel

# -----------------------------------------------------
# Categorías
# -----------------------------------------------------
class CategoriaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(CategoriaBase):
    pass


class Categoria(CategoriaBase):
    id: int

    class Config:
        orm_mode = True


# -----------------------------------------------------
# Productos
# -----------------------------------------------------
class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    codigo: Optional[str] = None
    precio_venta: float
    stock_actual: int = 0       # ✅ stock actual
    stock_minimo: int = 5       # ✅ stock mínimo
    activo: bool = True
    categoria_id: int


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    codigo: Optional[str] = None
    precio_venta: Optional[float] = None
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None
    activo: Optional[bool] = None
    categoria_id: Optional[int] = None


# -----------------------------------------------------
# Detalle de Cobro
# -----------------------------------------------------
class DetalleCobroBase(BaseModel):
    cobro_id: int
    cantidad: int
    subtotal: float


class DetalleCobroOut(DetalleCobroBase):
    id: int

    class Config:
        orm_mode = True


# -----------------------------------------------------
# Producto con relaciones (salida completa)
# -----------------------------------------------------
class Producto(ProductoBase):
    id: int
    categoria: Optional[Categoria] = None
    detalles_cobro: Optional[List[DetalleCobroOut]] = []  # 👈 Renombrado para coincidir con la relación SQLAlchemy

    class Config:
        orm_mode = True
