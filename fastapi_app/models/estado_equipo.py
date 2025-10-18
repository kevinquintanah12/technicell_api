# models/estado_equipo.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class EstadoEquipo(Base):
    __tablename__ = "estados_equipos"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id", ondelete="CASCADE"), nullable=False)
    estado = Column(String, nullable=False)  # "Recibido", "Diagnóstico", etc.
    fecha_inicio = Column(DateTime(timezone=True), server_default=func.now())
    fecha_fin = Column(DateTime(timezone=True), nullable=True)
    observaciones = Column(String, nullable=True)

    # Relación inversa
    equipo = relationship("Equipo", back_populates="historial_estados")
