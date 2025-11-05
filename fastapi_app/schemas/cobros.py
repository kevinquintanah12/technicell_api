from pydantic import BaseModel, condecimal
from datetime import datetime
from typing import Optional, List
from models.cobros import MetodoPagoEnum
from schemas.detalle_cobro import DetalleCobroCreate, DetalleCobroOut

class CobroBase(BaseModel):
    cliente_id: int
    equipo_id: int
    monto_total: condecimal(decimal_places=2, ge=0)
    anticipo: condecimal(decimal_places=2, ge=0)
    metodo_pago: MetodoPagoEnum

class CobroCreate(CobroBase):
    detalles: List[DetalleCobroCreate]  # ← Productos del cobro

class CobroUpdate(BaseModel):
    anticipo: Optional[condecimal(decimal_places=2, ge=0)]
    saldo_pendiente: Optional[condecimal(decimal_places=2, ge=0)]
    fecha_pago: Optional[datetime]

class CobroOut(CobroBase):
    id: int
    saldo_pendiente: float
    fecha_pago: datetime
    detalles: List[DetalleCobroOut] = []  # ← Productos asociados

    class Config:
        orm_mode = True
