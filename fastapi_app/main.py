from fastapi import FastAPI
from .routers import client
from .database import Base, engine

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Gestión - Clientes")

# Incluir rutas
app.include_router(client.router)
