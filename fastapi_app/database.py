# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 🔹 Leer la URL de la base de datos desde variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada. Define la variable de entorno en Render o localmente")

# 🔹 Crear engine
engine = create_engine(DATABASE_URL)

# 🔹 Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🔹 Base para modelos
Base = declarative_base()

# 🔹 Dependencia para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
