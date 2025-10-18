from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
from models.categoria import Categoria

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    codigo = Column(String, unique=True, nullable=True)
    precio_venta = Column(Float, nullable=False)
    activo = Column(Boolean, default=True)
    foto_url = Column(String, nullable=True)

    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    inventario = relationship(
        "Inventario", back_populates="producto", uselist=False
    )