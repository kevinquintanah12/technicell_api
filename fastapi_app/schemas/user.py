from pydantic import BaseModel, EmailStr
from typing import Optional
from models.user import UserRole

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Optional[UserRole] = UserRole.EMPLEADO

class UserRead(UserBase):
    id: int
    role: UserRole
    is_active: bool

    class Config:
        orm_mode = True
