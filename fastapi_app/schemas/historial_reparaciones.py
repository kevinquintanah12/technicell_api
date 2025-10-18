from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class HistorialReparacionBase(BaseModel):
    descripcion: str = Field(..., description="Detalle de la reparación")
    costo: float = Field(..., gt=0, description="Costo de la reparación")
    tecnico: Optional[str] = Field(None, description="Nombre del técnico")
    estado_post_reparacion: Optional[str] = "Pendiente"

class HistorialReparacionCreate(HistorialReparacionBase):
    pass

class HistorialReparacionOut(HistorialReparacionBase):
    id: int
    equipo_id: int
    fecha_reparacion: datetime

    class Config:
        from_attributes = True
