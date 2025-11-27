from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base

class IngresoReparacion(Base):
    __tablename__ = "ingreso_reparaciones"

    id = Column(Integer, primary_key=True, index=True)

    # FK opcional
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    # Datos capturados
    cliente_nombre = Column(String(150), nullable=False)
    telefono = Column(String(50), nullable=True)
    equipo = Column(String(150), nullable=False)
    marca = Column(String(150), nullable=True)
    modelo = Column(String(150), nullable=True)
    falla = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)

    # Información del ingreso
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)
    entregado = Column(Boolean, default=False)

    # Fotos
    foto1 = Column(String(255), nullable=True)
    foto2 = Column(String(255), nullable=True)
    foto3 = Column(String(255), nullable=True)

    cliente = relationship("Cliente", lazy="joined")
  