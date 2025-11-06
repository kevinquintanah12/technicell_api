# main.py

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base  # tu Base de modelos

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
from routers.detalle_cobro import router as detalle_cobro_router 

# Modelos (para que SQLAlchemy conozca las tablas)
from models.client import Cliente
from models.equipo import Equipo
from models.estado_equipo import EstadoEquipo
from models.historial_reparaciones import HistorialReparacion
from models.cobros import Cobro
from models.productos import Producto
from models.user import User
from models.detalle_cobro import DetalleCobro 

# 🔹 Configurar base de datos con variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")  # Debe estar configurada en Render/Aiven
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🔹 Crear tablas (solo si no usas Alembic)
Base.metadata.create_all(bind=engine)

# 🔹 Inicializar FastAPI
app = FastAPI(title="Technicell API")

# 🔹 Servir archivos estáticos (fotos)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 🔹 Incluir routers con prefijos claros
app.include_router(clientes_router, prefix="/clientes")
app.include_router(equipos_router, prefix="/equipos")
app.include_router(estados_router, prefix="/estados")
app.include_router(historial_routers, prefix="/historial")
app.include_router(cobros_router, prefix="/cobros")
app.include_router(inventario_router, prefix="/inventario")
app.include_router(categorias_router, prefix="/categorias")
app.include_router(producto_router, prefix="/productos")
app.include_router(user_router, prefix="/users")
app.include_router(detalle_cobro_router , prefix="/detalle-cobro")

# 🔹 Endpoint raíz simple
@app.get("/")
def root():
    return {"ok": True, "service": "Technicell API"}

# 🔹 Configuración para correr en Render
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
