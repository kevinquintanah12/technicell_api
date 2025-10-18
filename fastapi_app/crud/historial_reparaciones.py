from sqlalchemy.orm import Session
from models.historial_reparaciones import HistorialReparacion
from schemas.historial_reparaciones import HistorialReparacionCreate
from typing import List

def crear_reparacion(db: Session, equipo_id: int, payload: HistorialReparacionCreate) -> HistorialReparacion:
    reparacion = HistorialReparacion(
        equipo_id=equipo_id,
        descripcion=payload.descripcion,
        costo=payload.costo,
        tecnico=payload.tecnico,
        estado_post_reparacion=payload.estado_post_reparacion
    )
    db.add(reparacion)
    db.commit()
    db.refresh(reparacion)
    return reparacion

def listar_reparaciones_por_equipo(db: Session, equipo_id: int) -> List[HistorialReparacion]:
    return db.query(HistorialReparacion).filter(HistorialReparacion.equipo_id == equipo_id).order_by(HistorialReparacion.fecha_reparacion.desc()).all()
