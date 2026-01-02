from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator, EmailStr
from datetime import datetime


# ============================
# ESTADOS DEL EQUIPO
# ============================
EstadoEquipoLiteral = Literal[
    "recibido",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado",
    "pendientes",
]

# ============================
# TIPO DE CLAVE
# ============================
TipoClaveLiteral = Literal[
    "PIN",
    "Patron",
    "Contrasena",
]


# ============================
# BASE
# ============================
class EquipoBase(BaseModel):
    # -------- CLIENTE --------
    cliente_nombre: str = Field(..., min_length=1)
    cliente_numero: str = Field(..., min_length=8)
    cliente_correo: Optional[EmailStr] = None

    # -------- EQUIPO --------
    marca: Optional[str] = None
    modelo: str = Field(..., min_length=1)
    fallo: str = Field(..., min_length=1)
    observaciones: Optional[str] = None

    # -------- SEGURIDAD --------
    tipo_clave: TipoClaveLiteral
    clave_bloqueo: Optional[str] = None

    # -------- OTROS --------
    articulos_entregados: List[str] = Field(default_factory=list)
    estado: Optional[EstadoEquipoLiteral] = "pendientes"
    imei: Optional[str] = None

    @validator("imei")
    def validar_imei(cls, v):
        if v is None or v.strip() == "":
            return None

        if not v.isdigit():
            raise ValueError("El IMEI debe contener solo números")

        if len(v) != 15:
            raise ValueError("El IMEI debe tener exactamente 15 dígitos")

        return v


# ============================
# CREATE
# ============================
class EquipoCreate(EquipoBase):
    pass


# ============================
# UPDATE
# ============================
class EquipoUpdate(BaseModel):
    # -------- CLIENTE --------
    cliente_nombre: Optional[str] = None
    cliente_numero: Optional[str] = None
    cliente_correo: Optional[EmailStr] = None

    # -------- EQUIPO --------
    marca: Optional[str] = None
    modelo: Optional[str] = None
    fallo: Optional[str] = None
    observaciones: Optional[str] = None

    # -------- SEGURIDAD --------
    tipo_clave: Optional[TipoClaveLiteral] = None
    clave_bloqueo: Optional[str] = None

    # -------- OTROS --------
    articulos_entregados: Optional[List[str]] = None
    estado: Optional[EstadoEquipoLiteral] = None
    foto_url: Optional[str] = None
    imei: Optional[str] = None

    @validator("imei")
    def validar_imei(cls, v):
        if v is None or v.strip() == "":
            return None

        if not v.isdigit():
            raise ValueError("El IMEI debe contener solo números")

        if len(v) != 15:
            raise ValueError("El IMEI debe tener exactamente 15 dígitos")

        return v


# ============================
# RESPONSE
# ============================
class EquipoOut(BaseModel):
    id: int

    cliente_nombre: str
    cliente_numero: str
    cliente_correo: Optional[str]

    marca: Optional[str]
    modelo: str
    fallo: str
    observaciones: Optional[str]

    tipo_clave: TipoClaveLiteral
    # ⚠️ recomendado NO exponer la clave, pero la dejo por compatibilidad
    clave_bloqueo: Optional[str]

    articulos_entregados: List[str]
    estado: EstadoEquipoLiteral
    imei: Optional[str]

    fecha_ingreso: Optional[datetime]
    foto_url: Optional[str] = None

    class Config:
        orm_mode = True


# ==================================================
# NOTIFICACIONES (EXCLUSIVO DE EQUIPOS)
# ==================================================
class EquipoNotificar(BaseModel):
    """
    Schema exclusivo para notificar el estado de un equipo.
    Usado para correo / SMS / WhatsApp (según se implemente).
    """
    via: List[Literal["email", "phone"]]
    message: Optional[str] = None
