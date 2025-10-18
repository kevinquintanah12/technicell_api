# schemas/equipo.py
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator

# Estados permitidos del equipo
EstadoEquipoLiteral = Literal[
    "recibido",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado",
]


class EquipoBase(BaseModel):
    cliente_id: int = Field(..., description="ID del cliente asociado")
    marca: Optional[str] = None
    modelo: str = Field(..., min_length=1, description="Modelo del equipo (obligatorio)")
    fallo: str = Field(..., min_length=1, description="Fallo reportado (obligatorio)")
    observaciones: Optional[str] = None
    clave_bloqueo: Optional[str] = None
    articulos_entregados: List[str] = Field(default_factory=list)
    estado: Optional[EstadoEquipoLiteral] = "recibido"
    imei: Optional[str] = None  # 🔹 validación en @validator

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
    cliente_id: int
    marca: Optional[str]
    modelo: str
    fallo: str
    observaciones: Optional[str]
    clave_bloqueo: Optional[str]
    articulos_entregados: List[str]
    estado: EstadoEquipoLiteral
    imei: Optional[str]
    fecha_ingreso: Optional[str]
    foto_url: Optional[str] = None

    class Config:
        from_attributes = True  # Pydantic v2
