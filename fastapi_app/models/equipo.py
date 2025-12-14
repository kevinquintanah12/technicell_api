from sqlalchemy import (
    Column,
    Integer,
    String,
    JSON,
    DateTime,
    UniqueConstraint,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import requests


def get_internet_time() -> datetime:
    try:
        resp = requests.get(
            "http://worldtimeapi.org/api/timezone/Etc/UTC", timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            return datetime.fromisoformat(
                data["utc_datetime"].replace("Z", "+00:00")
            )
    except Exception:
        pass
    return datetime.utcnow()


class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)

    # ==========================
    # CLIENTE
    # ==========================
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)

    # Copias para evitar joins
    cliente_nombre = Column(String, nullable=False)
    cliente_numero = Column(String, nullable=False)
    cliente_correo = Column(String, nullable=True)

    cliente = relationship("Cliente", back_populates="equipos")

    # ==========================
    # ARCHIVOS
    # ==========================
    qr_url = Column(String, nullable=True)
    foto_url = Column(String, nullable=True)

    # ==========================
    # DATOS DEL EQUIPO
    # ==========================
    marca = Column(String, nullable=True)
    modelo = Column(String, nullable=False)
    fallo = Column(String, nullable=False)
    observaciones = Column(String, nullable=True)
    clave_bloqueo = Column(String, nullable=True)

    articulos_entregados = Column(JSON, default=list)

    estado = Column(String, default="recibido", index=True)
    imei = Column(String, unique=True, nullable=True)

    # ==========================
    # FECHAS
    # ==========================
    fecha_ingreso = Column(
        DateTime(timezone=True), default=get_internet_time
    )

    # 👉 cuando se marca como LISTO / ENTREGADO
    fecha_entrega = Column(DateTime(timezone=True), nullable=True)

    # ==========================
    # ARCHIVADO (NO APARECE EN LISTA)
    # ==========================
    archived = Column(Boolean, nullable=False, default=False, index=True)

    # ==========================
    # HISTORIALES
    # ==========================
    historial_estados = relationship(
        "EstadoEquipo",
        back_populates="equipo",
        cascade="all, delete-orphan",
    )

    historial_reparaciones = relationship(
        "HistorialReparacion",
        back_populates="equipo",
        cascade="all, delete-orphan",
    )

    cobros = relationship("Cobro", back_populates="equipo")

    __table_args__ = (
        UniqueConstraint("imei", name="uq_equipo_imei"),
    )
