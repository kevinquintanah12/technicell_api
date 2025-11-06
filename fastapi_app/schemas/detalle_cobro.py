from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DetalleCobroBase(BaseModel):
    producto_id: int
    cantidad: int

class DetalleCobroCreate(DetalleCobroBase):
    pass

class DetalleCobroRead(BaseModel):
    id: int
    producto_id: int
    producto_nombre: Optional[str]
    precio_unitario: Optional[float]
    cantidad: int
    subtotal: float
    fecha_registro: datetime

    class Config:
        orm_mode = True
