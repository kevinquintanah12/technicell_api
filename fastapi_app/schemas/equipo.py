# schemas/equipo.py
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator, EmailStr
from datetime import datetime  # ✅ Import necesario para datetime


EstadoEquipoLiteral = Literal[
    "recibido",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado",
]


class EquipoBase(BaseModel):
    cliente_nombre: str = Field(..., min_length=1)
    cliente_numero: str = Field(..., min_length=8)
    cliente_correo: Optional[EmailStr] = None

    marca: Optional[str] = None
    modelo: str = Field(..., min_length=1)
    fallo: str = Field(..., min_length=1)
    observaciones: Optional[str] = None
    clave_bloqueo: Optional[str] = None
    articulos_entregados: List[str] = Field(default_factory=list)
    estado: Optional[EstadoEquipoLiteral] = "recibido"
    imei: Optional[str] = None

    @validator("imei")
    def validar_imei(cls, v):
        if v is not None:
            if not v.isdigit():
                raise ValueError("El IMEI debe contener solo números")
            if len(v) != 15:
                raise ValueError("El IMEI debe tener exactamente 15 dígitos")
        return v


class EquipoCreate(EquipoBase):
    """Esquema para creación de equipos"""
    pass


class EquipoUpdate(BaseModel):
    cliente_nombre: Optional[str] = None
    cliente_numero: Optional[str] = None
    cliente_correo: Optional[EmailStr] = None

    marca: Optional[str] = None
    modelo: Optional[str] = None
    fallo: Optional[str] = None
    observaciones: Optional[str] = None
    clave_bloqueo: Optional[str] = None
    articulos_entregados: Optional[List[str]] = None
    estado: Optional[EstadoEquipoLiteral] = None
    foto_url: Optional[str] = None
    imei: Optional[str] = None

    @validator("imei")
    def validar_imei(cls, v):
        if v is not None:
            if not v.isdigit():
                raise ValueError("El IMEI debe contener solo números")
            if len(v) != 15:
                raise ValueError("El IMEI debe tener exactamente 15 dígitos")
        return v


class EquipoOut(BaseModel):
    id: int

    cliente_nombre: str
    cliente_numero: str
    cliente_correo: Optional[str]

    marca: Optional[str]
    modelo: str
    fallo: str
    observaciones: Optional[str]
    clave_bloqueo: Optional[str]
    articulos_entregados: List[str]
    estado: EstadoEquipoLiteral
    imei: Optional[str]
    fecha_ingreso: Optional[datetime]  # ✅ CAMBIO A datetime
    foto_url: Optional[str] = None

    class Config:
        orm_mode = True
