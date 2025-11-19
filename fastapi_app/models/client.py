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

    __table_args__ = (
        UniqueConstraint('telefono', name='uq_cliente_telefono'),
    )

    # ❌ ESTA RELACIÓN PROVOCABA EL ERROR
    # equipos = relationship(
    #     "Equipo",
    #     back_populates="cliente",
    #     cascade="all, delete-orphan"
    # )

    # Si Cobro sí necesita FK a Cliente, esta relación la dejamos
    cobros = relationship("Cobro", back_populates="cliente")
