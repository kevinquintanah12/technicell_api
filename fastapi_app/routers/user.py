from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from schemas.user import UserCreate, UserRead
from crud import user as crud_user
from utils.security import verify_password
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])

# -----------------------------
# Crear usuario
# -----------------------------
@router.post("/", response_model=UserRead)
def create_new_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud_user.create_user(db, user)

# -----------------------------
# Obtener todos los usuarios
# -----------------------------
@router.get("/get", response_model=list[UserRead])
def get_all_users(db: Session = Depends(get_db)):
    users = crud_user.get_users(db)
    return users

# -----------------------------
# Schemas para login
# -----------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool

# -----------------------------
# Iniciar sesión
# -----------------------------
@router.post("/login", response_model=LoginResponse)
def login(user: LoginRequest, db: Session = Depends(get_db)):
    db_user = crud_user.get_user_by_email(db, user.email)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    # ✅ Login exitoso
    return LoginResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        role=db_user.role.value if hasattr(db_user.role, "value") else db_user.role,
        is_active=db_user.is_active
    )
