from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class IngresoReparacion(Base):
    __tablename__ = "ingreso_reparaciones"

    id = Column(Integer, primary_key=True, index=True)

    # Cliente (ID opcional)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)

    # Datos enviados desde Flutter
    cliente_nombre = Column(String(150), nullable=False)
    equipo = Column(String(150), nullable=False)
    modelo = Column(String(150), nullable=True)
    imei = Column(String(50), nullable=True)

    falla_reportada = Column(Text, nullable=False)
    observaciones = Column(Text, nullable=True)

    # Información de cobro
    anticipo = Column(Float, nullable=False, default=0)
    total_estimado = Column(Float, nullable=False)
    tipo_pago = Column(String(50), nullable=False)
    monto_recibido = Column(Float, nullable=False)

    # Control
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)
    entregado = Column(Boolean, default=False)

    # Relación con cliente
    cliente = relationship("Cliente", lazy="joined")
