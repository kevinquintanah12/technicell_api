from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class IngresoReparacion(Base):
    __tablename__ = "ingresos_reparacion"

    id = Column(Integer, primary_key=True, index=True)

    # Cliente (puede ser texto directo o FK a otra tabla)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    cliente_nombre = Column(String(200), nullable=False)

    # Datos del equipo
    equipo = Column(String(200), nullable=False)              # Ej: iPhone 13
    modelo = Column(String(200), nullable=True)               # Ej: A2633
    imei = Column(String(40), nullable=True)
    falla_reportada = Column(Text, nullable=False)
    observaciones = Column(Text, nullable=True)

    # Datos económicos
    anticipo = Column(Float, default=0.0)
    total_estimado = Column(Float, default=0.0)
    total_final = Column(Float, default=0.0)

    # Estados posibles: "Ingresado", "En Proceso", "Listo", "Entregado"
    estado = Column(String(50), default="Ingresado")

    # Auditoría
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación opcional hacia cliente
    cliente = relationship("Cliente", back_populates="reparaciones", lazy="joined")
