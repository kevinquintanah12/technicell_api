# crud/equipos.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from models.equipo import Equipo, EstadoEquipo
from schemas.equipo import EquipoCreate, EquipoUpdate

def create_equipo(db: Session, payload: EquipoCreate) -> Equipo:
    estado = EstadoEquipo(payload.estado) if payload.estado else EstadoEquipo.recibido
    db_obj = Equipo(
        cliente_id=payload.cliente_id,
        marca=payload.marca,
        modelo=payload.modelo,
        fallo=payload.fallo,
        observaciones=payload.observaciones,
        clave_bloqueo=payload.clave_bloqueo,
        articulos_entregados=payload.articulos_entregados or [],
        estado=estado,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_equipo(db: Session, equipo_id: int) -> Optional[Equipo]:
    return db.get(Equipo, equipo_id)

def list_equipos(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    cliente_id: Optional[int] = None,
    estado: Optional[str] = None,
) -> List[Equipo]:
    stmt = select(Equipo)
    if cliente_id is not None:
        stmt = stmt.where(Equipo.cliente_id == cliente_id)
    if estado is not None:
        # convierte string a Enum si viene correcto
        try:
            enum_estado = EstadoEquipo(estado)
            stmt = stmt.where(Equipo.estado == enum_estado)
        except ValueError:
            # estado inválido: retorna vacío (o podrías omitir filtro)
            stmt = stmt.where(Equipo.id == -1)
    stmt = stmt.order_by(Equipo.fecha_ingreso.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())

def update_equipo(db: Session, equipo_id: int, payload: EquipoUpdate) -> Optional[Equipo]:
    obj = db.get(Equipo, equipo_id)
    if not obj:
        return None

    if payload.marca is not None:
        obj.marca = payload.marca
    if payload.modelo is not None:
        obj.modelo = payload.modelo
    if payload.fallo is not None:
        obj.fallo = payload.fallo
    if payload.observaciones is not None:
        obj.observaciones = payload.observaciones
    if payload.clave_bloqueo is not None:
        obj.clave_bloqueo = payload.clave_bloqueo
    if payload.articulos_entregados is not None:
        obj.articulos_entregados = payload.articulos_entregados
    if payload.estado is not None:
        obj.estado = EstadoEquipo(payload.estado)

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def delete_equipo(db: Session, equipo_id: int) -> bool:
    obj = db.get(Equipo, equipo_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True

def set_equipo_foto(db: Session, equipo_id: int, foto_url: str) -> Optional[Equipo]:
    obj = db.get(Equipo, equipo_id)
    if not obj:
        return None
    obj.foto_url = foto_url
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
