# main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import Base, engine

# Routers
from routers.client import router as clientes_router
from routers.equipos import router as equipos_router
from routers.estados_equipo import router as estados_router
from routers.historial_reparaciones import router as historial_routers
from routers.cobros import router as cobros_router
from routers.inventario import router as inventario_router
from routers.categorias import router as categorias_router
from routers.productos import router as producto_router
from routers.user import router as user_router


# Modelos (para que SQLAlchemy conozca las tablas)
from models.client import Cliente
from models.equipo import Equipo
from models.estado_equipo import EstadoEquipo
from models.historial_reparaciones import HistorialReparacion
from models.cobros import Cobro
from models.productos import Producto
from models.user import User


app = FastAPI(title="Technicell API")

# 🔹 Crear tablas en la base de datos (si no usas Alembic)
Base.metadata.create_all(bind=engine)

# 🔹 Servir archivos estáticos (fotos)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔹 Incluir routers
app.include_router(clientes_router)  # /clientes
app.include_router(equipos_router)    # /equipos
app.include_router(estados_router)    # /equipos
app.include_router(historial_routers)    # /equipos
app.include_router(user_router)    # /equipos

# 🔹 Endpoint raíz simple
@app.get("/")
def root():
    return {"ok": True, "service": "Technicell API"}
