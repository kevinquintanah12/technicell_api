from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False)
    codigo = Column(String, unique=True, nullable=True)
    precio_venta = Column(Float, nullable=False)

    # 🧾 Gestión de inventario
    stock_actual = Column(Integer, default=0, nullable=False)  # Stock actual del producto
    stock_minimo = Column(Integer, default=5, nullable=False)   # Nivel mínimo antes de alerta

    activo = Column(Boolean, default=True)
    foto_url = Column(String, nullable=True)

    # 🔗 Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    detalles_cobro = relationship("DetalleCobro", back_populates="producto")
