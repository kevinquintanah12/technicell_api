from sqlalchemy import Column, Integer, String, UniqueConstraint
from ..database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String, nullable=False)
    telefono = Column(String, unique=True, nullable=False)
    correo = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint('telefono', name='uq_cliente_telefono'),)
