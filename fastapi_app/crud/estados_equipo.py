# crud/estados_equipo.py
from sqlalchemy.orm import Session
from models.estado_equipo import EstadoEquipo
from schemas.estado_equipo import EstadoEquipoCreate
from typing import List

VALID_ESTADOS = ["recibido", "diagnostico", "en_reparacion", "listo", "entregado", "cancelado"]

def crear_estado_equipo(db: Session, equipo_id: int, payload: EstadoEquipoCreate) -> EstadoEquipo:
    if payload.estado not in VALID_ESTADOS:
        raise ValueError("Estado inválido")

    estado = EstadoEquipo(
        equipo_id=equipo_id,
        estado=payload.estado,
        observaciones=payload.observaciones,
    )
    db.add(estado)
    db.commit()
    db.refresh(estado)
    return estado

def listar_estados_equipo(db: Session, equipo_id: int) -> List[EstadoEquipo]:
    return (
        db.query(EstadoEquipo)
        .filter(EstadoEquipo.equipo_id == equipo_id)
        .order_by(EstadoEquipo.fecha_inicio.desc())
        .all()
    )
