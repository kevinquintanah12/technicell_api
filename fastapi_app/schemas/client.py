# schemas/cliente.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional


class ClientBase(BaseModel):
    nombre_completo: str
    telefono: str
    correo: Optional[EmailStr] = None

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
    pass


class ClientUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[EmailStr] = None

    @validator("nombre_completo")
    def nombre_no_vacio(cls, v: Optional[str]):
        if v is not None and not v.strip():
            raise ValueError("El nombre del cliente no puede estar vacío")
        return v

    @validator("telefono")
    def telefono_valido(cls, v: Optional[str]):
        if v is not None:
            if not v.isdigit():
                raise ValueError("El teléfono debe contener solo dígitos")
            if len(v) < 8:
                raise ValueError("El teléfono debe tener al menos 8 dígitos")
        return v


class ClientOut(ClientBase):
    id: int

    class Config:
        orm_mode = True
