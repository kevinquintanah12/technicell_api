from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

class MetodoPagoEnum(str, enum.Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    transferencia = "transferencia"

class Cobro(Base):
    __tablename__ = "cobros"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    equipo_id = Column(Integer, ForeignKey("equipos.id"))
    monto_total = Column(Float, nullable=False)
    anticipo = Column(Float, default=0.0)
    saldo_pendiente = Column(Float, nullable=False)
    fecha_pago = Column(DateTime, default=datetime.utcnow)
    metodo_pago = Column(Enum(MetodoPagoEnum), nullable=False)

    cliente = relationship("Cliente", back_populates="cobros")
    equipo = relationship("Equipo", back_populates="cobros")
