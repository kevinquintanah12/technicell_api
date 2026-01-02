from typing import List, Optional, Literal
from pydantic import BaseModel, Field, EmailStr, field_validator
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

TipoClaveLiteral = Literal[
    "PIN",
    "PATRON",
    "NINGUNA",
]

# ============================
# BASE
# ============================
class EquipoBase(BaseModel):
    cliente_nombre: str = Field(..., min_length=1)
    cliente_numero: str = Field(..., min_length=8)
    cliente_correo: Optional[EmailStr] = None

    marca: Optional[str] = None
    modelo: str = Field(..., min_length=1)
    fallo: str = Field(..., min_length=1)
    observaciones: Optional[str] = None

    tipo_clave: TipoClaveLiteral = "NINGUNA"
    clave_bloqueo: Optional[str] = None

    # ⚠️ SOLO PARA FRONT (NO SE GUARDA EN BD)
    pin: Optional[str] = None

    articulos_entregados: List[str] = Field(default_factory=list)
    estado: Optional[EstadoEquipoLiteral] = "pendientes"
    imei: Optional[str] = None
    precio_estimado: Optional[float] = None

    @field_validator("imei")
    @classmethod
    def validar_imei(cls, v):
        if v is None or v.strip() == "":
            return None
        if not v.isdigit():
            raise ValueError("El IMEI debe contener solo números")
        if len(v) != 15:
            raise ValueError("El IMEI debe tener exactamente 15 dígitos")
        return v

    @field_validator("clave_bloqueo", mode="before")
    @classmethod
    def validar_clave_bloqueo(cls, v, info):
        tipo = info.data.get("tipo_clave")
        if tipo == "PIN":
            if not v:
                raise ValueError("La clave PIN es obligatoria")
            if not v.isdigit() or len(v) < 4:
                raise ValueError("El PIN debe ser numérico y mínimo 4 dígitos")
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
    cliente_nombre: Optional[str] = None
    cliente_numero: Optional[str] = None
    cliente_correo: Optional[EmailStr] = None

    marca: Optional[str] = None
    modelo: Optional[str] = None
    fallo: Optional[str] = None
    observaciones: Optional[str] = None

    tipo_clave: Optional[TipoClaveLiteral] = None
    clave_bloqueo: Optional[str] = None
    pin: Optional[str] = None

    articulos_entregados: Optional[List[str]] = None
    estado: Optional[EstadoEquipoLiteral] = None
    foto_url: Optional[str] = None
    imei: Optional[str] = None
    precio_estimado: Optional[float] = None

    @field_validator("imei")
    @classmethod
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
    clave_bloqueo: Optional[str]

    articulos_entregados: List[str]
    estado: EstadoEquipoLiteral
    imei: Optional[str]
    precio_estimado: Optional[float]

    fecha_ingreso: Optional[datetime]
    fecha_entrega: Optional[datetime]

    qr_url: Optional[str] = None
    foto_url: Optional[str] = None

    # 🔥 ESTA ES LA CLAVE PARA PYDANTIC V2 🔥
    model_config = {
        "from_attributes": True
    }


# ==================================================
# NOTIFICACIONES
# ==================================================
class EquipoNotificar(BaseModel):
    via: List[Literal["email", "phone"]]
    message: Optional[str] = None
