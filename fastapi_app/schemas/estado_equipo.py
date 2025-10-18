# schemas/estado_equipo.py
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class EstadoEquipoBase(BaseModel):
    estado: str
    observaciones: Optional[str] = None

class EstadoEquipoCreate(EstadoEquipoBase):
    pass

class EstadoEquipoOut(BaseModel):
    id: int
    equipo_id: int
    estado: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime]
    observaciones: Optional[str]

    class Config:
        from_attributes = True
