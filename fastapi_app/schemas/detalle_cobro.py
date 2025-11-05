from pydantic import BaseModel, condecimal
from typing import Optional
from datetime import datetime

class DetalleCobroBase(BaseModel):
    cobro_id: int
    producto_id: int
    cantidad: int

class DetalleCobroCreate(DetalleCobroBase):
    pass

class DetalleCobroUpdate(BaseModel):
    cantidad: Optional[int] = None
    precio_unitario: Optional[condecimal(decimal_places=2, ge=0)] = None

class DetalleCobroRead(BaseModel):
    id: int
    cobro_id: int
    producto_id: int
    producto_nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float
    fecha_registro: datetime

    class Config:
        orm_mode = True
