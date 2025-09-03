# models/equipo.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func
import enum

from database import Base

class EstadoEquipo(enum.Enum):
    recibido = "recibido"
    diagnostico = "diagnostico"
    en_reparacion = "en_reparacion"
    listo = "listo"
    entregado = "entregado"
    cancelado = "cancelado"

class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)

    foto_url = Column(String, nullable=True)  # ej: "/static/uploads/equipos/uuid.jpg"
    marca = Column(String, nullable=True)
    modelo = Column(String, nullable=False)   # Validación: obligatorio
    fallo = Column(Text, nullable=False)      # Validación: obligatorio
    observaciones = Column(Text, nullable=True)
    clave_bloqueo = Column(String, nullable=True)  # contraseña/patrón (opcional)

    # Lista de accesorios entregados (array de texto en Postgres)
    articulos_entregados = Column(ARRAY(String), nullable=False, server_default="{}")

    estado = Column(
        Enum(EstadoEquipo, name="estado_equipo"),
        nullable=False,
        default=EstadoEquipo.recibido
    )

    # Fecha automática
    fecha_ingreso = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
