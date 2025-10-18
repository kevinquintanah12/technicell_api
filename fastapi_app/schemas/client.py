# schemas/cliente.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from schemas.equipo import EquipoOut  # 👈 importamos el schema de Equipo


class ClientBase(BaseModel):
    nombre_completo: str
    telefono: str
    correo: Optional[EmailStr] = None  # valida automáticamente el formato de correo

    # 🔹 Validaciones personalizadas
    @validator("nombre_completo")
    def nombre_no_vacio(cls, v: str):
        if not v.strip():
            raise ValueError("El nombre del cliente no puede estar vacío")
        return v

    @validator("telefono")
    def telefono_valido(cls, v: str):
        if not v.isdigit():
            raise ValueError("El teléfono debe contener solo dígitos")
        if len(v) < 8:
            raise ValueError("El teléfono debe tener al menos 8 dígitos")
        return v


class ClientCreate(ClientBase):
    """Esquema para creación de clientes"""
    pass


class ClientUpdate(BaseModel):
    """Esquema para actualización parcial de clientes"""
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[EmailStr] = None

    # ✅ Si se envía un nombre, validamos que no esté vacío
    @validator("nombre_completo")
    def nombre_no_vacio(cls, v: Optional[str]):
        if v is not None and not v.strip():
            raise ValueError("El nombre del cliente no puede estar vacío")
        return v

    # ✅ Validación opcional del teléfono
    @validator("telefono")
    def telefono_valido(cls, v: Optional[str]):
        if v is not None:
            if not v.isdigit():
                raise ValueError("El teléfono debe contener solo dígitos")
            if len(v) < 8:
                raise ValueError("El teléfono debe tener al menos 8 dígitos")
        return v


class ClientOut(ClientBase):
    """Respuesta al consultar clientes"""
    id: int
    equipos: List[EquipoOut] = []  # 👈 relación Cliente → lista de equipos

    class Config:
        orm_mode = True  # ✅ permite convertir modelos SQLAlchemy a Pydantic
