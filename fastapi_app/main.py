# main.py

from database import Base, engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from models.client import Client
from models.equipo import Equipo
from routers.equipos import router


# Importa modelos para que SQLAlchemy los conozca antes de create_all
#from models import equipo as equipo_model  # importa el módulo para registrar el modelo
# from routers.equipos import router as equipos_router

app = FastAPI(title="Technicell API")

# Crea tablas si no usas Alembic (ya también está en el router por seguridad)
Base.metadata.create_all(bind=engine)

# Servir archivos estáticos (fotos)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rutas
app.include_router(router)

# Opcional: raíz simple
@app.get("/")
def root():
    return {"ok": True, "service": "Technicell API"}
