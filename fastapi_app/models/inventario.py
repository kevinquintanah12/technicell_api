from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import requests

def get_internet_time() -> datetime:
    """
    Obtiene la hora actual desde un servidor de internet.
    """
    try:
        resp = requests.get("http://worldtimeapi.org/api/timezone/Etc/UTC", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return datetime.fromisoformat(data["utc_datetime"].replace("Z", "+00:00"))
    except Exception:
        pass
    return datetime.utcnow()

class Inventario(Base):
    __tablename__ = "inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), unique=True, nullable=False)
    stock_actual = Column(Integer, default=0)
    stock_minimo = Column(Integer, default=5)
    fecha_ultima_actualizacion = Column(DateTime(timezone=True), default=get_internet_time)

    # Relación
    producto = relationship("Producto", back_populates="inventario")