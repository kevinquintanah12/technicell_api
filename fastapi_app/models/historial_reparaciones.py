from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class HistorialReparacion(Base):
    __tablename__ = "historial_reparaciones"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False)
    fecha_reparacion = Column(DateTime, default=func.now())
    descripcion = Column(String, nullable=False)
    costo = Column(Float, nullable=False)
    tecnico = Column(String, nullable=True)
    estado_post_reparacion = Column(String, default="Pendiente")

    equipo = relationship("Equipo", back_populates="historial_reparaciones")
