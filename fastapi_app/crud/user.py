from sqlalchemy.orm import Session
from models.user import User, UserRole
from schemas.user import UserCreate
from utils.security import get_password_hash  # función para hashear contraseñas


# -----------------------------
# Crear un nuevo usuario
# -----------------------------
def create_user(db: Session, user: UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# -----------------------------
# Obtener un usuario por email
# -----------------------------
def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


# -----------------------------
# Obtener un usuario por nombre de usuario
# -----------------------------
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


# -----------------------------
# Obtener todos los usuarios
# -----------------------------
def get_users(db: Session):
    return db.query(User).all()
