# utils/security.py
from passlib.context import CryptContext

# Configuramos bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica que la contraseña coincida con su hash"""
    return pwd_context.verify(plain_password, hashed_password)
