from pydantic import BaseModel, condecimal
from datetime import datetime
from typing import Optional
from models.cobros import MetodoPagoEnum

class CobroBase(BaseModel):
    cliente_id: int
    equipo_id: int
    monto_total: condecimal(decimal_places=2, ge=0)
    anticipo: condecimal(decimal_places=2, ge=0)
    metodo_pago: MetodoPagoEnum

class CobroCreate(CobroBase):
    pass

class CobroUpdate(BaseModel):
    anticipo: Optional[condecimal(decimal_places=2, ge=0)]
    saldo_pendiente: Optional[condecimal(decimal_places=2, ge=0)]
    fecha_pago: Optional[datetime]

class CobroOut(CobroBase):
    id: int
    saldo_pendiente: float
    fecha_pago: datetime

    class Config:
        orm_mode = True
