from typing import Optional
from pydantic import BaseModel

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

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    codigo: Optional[str] = None
    precio_venta: float
    activo: bool = True
    categoria_id: int

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(ProductoBase):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    codigo: Optional[str] = None
    precio_venta: Optional[float] = None
    activo: Optional[bool] = None
    categoria_id: Optional[int] = None

class Producto(ProductoBase):
    id: int
    class Config:
        orm_mode = True
        
class InventarioBase(BaseModel):
    stock_actual: int
    stock_minimo: int

class InventarioCreate(InventarioBase):
    producto_id: int

class InventarioUpdate(BaseModel):
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None

class Inventario(InventarioBase):
    id: int
    producto_id: int
    class Config:
        orm_mode = True