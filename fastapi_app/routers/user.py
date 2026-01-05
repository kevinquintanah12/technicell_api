# users_router.py
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db
from schemas.user import UserCreate, UserRead  # usa tus schemas reales
from crud import user as crud_user
from utils.security import verify_password  # si usas auth local

router = APIRouter(prefix="/users", tags=["users"])


# --- Helpers / schemas locales (si no los tienes en schemas/user.py puedes moverlos allí) ---
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool


# -----------------------------
# Crear usuario (empleado)
# -----------------------------
@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo usuario/empleado.
    Verifica si el email ya existe y, si no, delega en crud_user.create_user().
    """
    db_user = crud_user.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    return crud_user.create_user(db, user)


# -----------------------------
# Obtener listado de usuarios (con búsqueda y paginado)
# -----------------------------
@router.get("/", response_model=List[UserRead])
def list_users(
    q: Optional[str] = Query(None, description="Texto de búsqueda (username o email)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Lista usuarios. Parámetros opcionales:
    - q: buscar por username o email (implementarlo en crud_user.get_users)
    - skip, limit: paginado
    """
    # Se asume que crud_user.get_users soporta (db, skip, limit, q)
    users = crud_user.get_users(db, skip=skip, limit=limit, q=q)
    return users


# -----------------------------
# Obtener usuario por id
# -----------------------------
@router.get("/{user_id}", response_model=UserRead)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    user = crud_user.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


# -----------------------------
# Actualizar usuario (parcial)
# -----------------------------
@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    """
    Actualiza campos del usuario (parcial). Si se cambia email, verifica unicidad.
    """
    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # si actualizan email, validar que no exista otro usuario con ese email
    if user_in.email and user_in.email != db_user.email:
        other = crud_user.get_user_by_email(db, user_in.email)
        if other and other.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered by another user")

    updated = crud_user.update_user(db, db_user, user_in)  # implementa lógica de merge en crud
    return updated


# -----------------------------
# Dar de baja (desactivar) un usuario
# -----------------------------
@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(user_id: int, db: Session = Depends(get_db)):
    """
    Marca is_active = False. No borra físicamente.
    """
    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Reusa update_user o función específica
    updated = crud_user.update_user(db, db_user, {"is_active": False})
    return updated


# -----------------------------
# Reactivar usuario
# -----------------------------
@router.post("/{user_id}/reactivate", response_model=UserRead)
def reactivate_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    updated = crud_user.update_user(db, db_user, {"is_active": True})
    return updated


# -----------------------------
# Eliminar usuario (borrado físico)
# -----------------------------
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """
    Borrado físico del usuario. Puedes reemplazar por soft-delete si lo prefieres.
    """
    db_user = crud_user.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    crud_user.delete_user(db, db_user)
    return None


# -----------------------------
# Login (tu endpoint original, con pequeñas mejoras)
# -----------------------------
@router.post("/login", response_model=LoginResponse)
def login(user: LoginRequest, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, user.email)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return LoginResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        role=db_user.role.value if hasattr(db_user.role, "value") else db_user.role,
        is_active=db_user.is_active,
    )
