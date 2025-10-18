# models/cliente.py
from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String, nullable=False)
    telefono = Column(String, unique=True, nullable=False)
    correo = Column(String, nullable=True)

    # 🔹 Evitamos IMEIs duplicados por cliente (si IMEI está en la tabla equipos)
    __table_args__ = (
        UniqueConstraint('telefono', name='uq_cliente_telefono'),
    )

    equipos = relationship(
        "Equipo",
        back_populates="cliente",
        cascade="all, delete-orphan"
    )

    cobros = relationship("Cobro", back_populates="cliente")

