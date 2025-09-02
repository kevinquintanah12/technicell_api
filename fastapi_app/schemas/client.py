from pydantic import BaseModel, EmailStr
from typing import Optional

class ClientBase(BaseModel):
    nombre_completo: str
    telefono: str
    correo: Optional[EmailStr] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[EmailStr] = None

class ClientOut(ClientBase):
    id: int

    class Config:
        orm_mode = True  # ✅ así FastAPI puede convertir modelos SQLAlchemy a Pydantic
