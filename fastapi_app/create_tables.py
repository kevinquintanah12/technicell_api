from models.client import Client
from models.equipo import Equipo
from database import Base, engine

Base.metadata.create_all(bind=engine)
print("Tablas creadas correctamente")
