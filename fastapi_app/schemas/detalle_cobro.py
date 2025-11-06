from pydantic import BaseModel

class DetalleCobroBase(BaseModel):
    producto_id: int
    cantidad: int

class DetalleCobroCreate(DetalleCobroBase):
    pass

class DetalleCobro(DetalleCobroBase):
    id: int
    subtotal: float

    class Config:
        orm_mode = True
