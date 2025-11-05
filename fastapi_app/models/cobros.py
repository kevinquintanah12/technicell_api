from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import enum

# -----------------------------
# Enumerador de métodos de pago
# -----------------------------
class MetodoPagoEnum(str, enum.Enum):
    efectivo = "efectivo"
    tarjeta = "tarjeta"
    transferencia = "transferencia"

# -----------------------------
# Modelo principal: Cobro
# -----------------------------
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

    # Relaciones
    cliente = relationship("Cliente", back_populates="cobros")
    equipo = relationship("Equipo", back_populates="cobros")

    # Relación con los productos (vía tabla intermedia)
    detalles = relationship(
        "DetalleCobro",
        back_populates="cobro",
        cascade="all, delete-orphan"
    )


# -----------------------------
# Modelo intermedio: DetalleCobro
# -----------------------------
class DetalleCobro(Base):
    __tablename__ = "detalles_cobro"

    id = Column(Integer, primary_key=True, index=True)
    cobro_id = Column(Integer, ForeignKey("cobros.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relaciones
    cobro = relationship("Cobro", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_cobro")
