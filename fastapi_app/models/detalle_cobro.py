from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class DetalleCobro(Base):
    __tablename__ = "detalles_cobro"

    id = Column(Integer, primary_key=True, index=True)
    cobro_id = Column(Integer, ForeignKey("cobros.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    producto_nombre = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    cobro = relationship("Cobro", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_cobro")
