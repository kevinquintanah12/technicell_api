# crud/user.py
from typing import Optional, Union, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models.user import User, UserRole
from schemas.user import UserCreate
from utils.security import get_password_hash

# -----------------------------
# Crear un nuevo usuario
# -----------------------------
def create_user(db: Session, user: UserCreate) -> User:
    """
    Crea y persiste un usuario. `user` es un Pydantic UserCreate.
    Hashea la contraseña antes de guardar.
    """
    # Si role viene como string, intentar convertirlo al enum
    role_value = user.role
    try:
        if isinstance(role_value, str):
            role_value = UserRole(role_value)
    except Exception:
        # Si no se puede convertir, dejar como viene (asume que el modelo lo validará)
        pass

    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=role_value,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# -----------------------------
# Obtener un usuario por id
# -----------------------------
def get_user(db: Session, user_id: int) -> Optional[User]:
    """
    Devuelve el usuario por su id o None si no existe.
    """
    return db.query(User).filter(User.id == user_id).first()


# -----------------------------
# Obtener un usuario por email
# -----------------------------
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


# -----------------------------
# Obtener un usuario por nombre de usuario
# -----------------------------
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


# -----------------------------
# Obtener todos los usuarios (con búsqueda y paginado)
# -----------------------------
def get_users(db: Session, skip: int = 0, limit: int = 100, q: Optional[str] = None):
    """
    Lista usuarios.
    - q: texto opcional para buscar en username o email (case-insensitive, LIKE)
    - skip, limit: paginado
    """
    query = db.query(User)
    if q:
        like_q = f"%{q}%"
        query = query.filter(or_(User.username.ilike(like_q), User.email.ilike(like_q)))
    query = query.order_by(User.id).offset(skip).limit(limit)
    return query.all()


# -----------------------------
# Actualizar usuario (parcial)
# -----------------------------
def update_user(db: Session, db_user: User, update_data: Union[Dict[str, Any], object]) -> User:
    """
    Actualiza campos de db_user con los valores de update_data.
    update_data puede ser:
      - un dict con claves/valores
      - un Pydantic model (p.ej. UserUpdate) — en cuyo caso se usa .dict(exclude_unset=True)
    Maneja `password` (hashea) y conversión de `role` si viene como string.
    Devuelve el usuario actualizado (refreshed).
    """
    # Normalizar update_data a dict
    if not isinstance(update_data, dict):
        # Pydantic model -> dict sin unset
        try:
            update_dict = update_data.dict(exclude_unset=True)
        except Exception:
            # Fallback: intentar convertir directamente a dict
            update_dict = dict(update_data)
    else:
        update_dict = update_data.copy()

    # Si viene password, hashearla y guardar en hashed_password
    if "password" in update_dict and update_dict["password"] is not None:
        update_dict["hashed_password"] = get_password_hash(update_dict.pop("password"))

    # Si cambia role y es string, intentar convertir a enum
    if "role" in update_dict and update_dict["role"] is not None:
        try:
            if isinstance(update_dict["role"], str):
                update_dict["role"] = UserRole(update_dict["role"])
        except Exception:
            # dejar tal cual (posible validación posterior)
            pass

    # Aplicar cambios
    for field, value in update_dict.items():
        # Evitar asignar keys que no sean columnas del modelo
        if hasattr(db_user, field):
            setattr(db_user, field, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# -----------------------------
# Eliminar usuario (borrado físico)
# -----------------------------
def delete_user(db: Session, db_user: User) -> None:
    """
    Borra físicamente el registro del usuario.
    Si prefieres soft-delete, puedes en lugar de esto hacer:
        db_user.is_active = False
        db.add(db_user)
        db.commit()
    """
    db.delete(db_user)
    db.commit()
    return None
