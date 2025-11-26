from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IngresoReparacionBase(BaseModel):
    cliente_nombre: str
    equipo: str
    modelo: Optional[str] = None
    imei: Optional[str] = None
    falla_reportada: str
    observaciones: Optional[str] = None
    anticipo: float = 0.0
    total_estimado: float = 0.0


class IngresoReparacionCreate(IngresoReparacionBase):
    cliente_id: Optional[int] = None


class IngresoReparacionUpdate(BaseModel):
    estado: Optional[str] = None
    total_final: Optional[float] = None
    observaciones: Optional[str] = None


class IngresoReparacionOut(IngresoReparacionBase):
    id: int
    estado: str
    fecha_ingreso: datetime
    fecha_actualizacion: datetime

    class Config:
        orm_mode = True
