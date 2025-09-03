# schemas/equipo.py
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

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
    clave_bloqueo: Optional[str] = Field(
        default=None, description="Contraseña/patrón si el cliente la proporciona"
    )
    articulos_entregados: List[str] = Field(default_factory=list)
    estado: Optional[EstadoEquipoLiteral] = "recibido"  # opcional al crear

class EquipoCreate(EquipoBase):
    pass  # fecha_ingreso es automática; foto se sube por endpoint aparte

class EquipoUpdate(BaseModel):
    # todos opcionales para PATCH
    marca: Optional[str] = None
    modelo: Optional[str] = None
    fallo: Optional[str] = None
    observaciones: Optional[str] = None
    clave_bloqueo: Optional[str] = None
    articulos_entregados: Optional[List[str]] = None
    estado: Optional[EstadoEquipoLiteral] = None

class EquipoOut(BaseModel):
    id: int
    cliente_id: int
    foto_url: Optional[str]
    marca: Optional[str]
    modelo: str
    fallo: str
    observaciones: Optional[str]
    clave_bloqueo: Optional[str]
    articulos_entregados: List[str]
    estado: EstadoEquipoLiteral
    fecha_ingreso: str

    class Config:
        from_attributes = True  # Pydantic v2 (en v1: orm_mode = True)
