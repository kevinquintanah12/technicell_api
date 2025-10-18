from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from models.equipo import Equipo
from models.client import Cliente
from schemas.equipo import EquipoCreate, EquipoUpdate, EstadoEquipoLiteral

VALID_ESTADOS = ["recibido", "diagnostico", "en_reparacion", "listo", "entregado", "cancelado"]

# 🔹 Crear equipo
def create_equipo(db: Session, payload: EquipoCreate) -> Equipo:
    estado = payload.estado if payload.estado in VALID_ESTADOS else "recibido"
    db_obj = Equipo(
        cliente_id=payload.cliente_id,
        marca=payload.marca,
        modelo=payload.modelo,
        fallo=payload.fallo,
        observaciones=payload.observaciones,
        clave_bloqueo=payload.clave_bloqueo,
        articulos_entregados=payload.articulos_entregados or [],
        estado=estado,
        fecha_ingreso=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

# 🔹 Obtener equipo por ID
def get_equipo(db: Session, equipo_id: int) -> Optional[Equipo]:
    return db.get(Equipo, equipo_id)

# 🔹 Listar equipos con filtros
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
        if estado in VALID_ESTADOS:
            stmt = stmt.where(Equipo.estado == estado)
        else:
            stmt = stmt.where(Equipo.id == -1)  # devuelve vacío si estado inválido
    stmt = stmt.order_by(Equipo.fecha_ingreso.desc()).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())

# 🔹 Obtener equipos de un cliente por ID
def get_equipos_by_cliente(db: Session, cliente_id: int) -> List[Equipo]:
    return db.query(Equipo).filter(Equipo.cliente_id == cliente_id).order_by(Equipo.fecha_ingreso.desc()).all()

# 🔹 Buscar equipos por nombre de cliente (flexible)
def get_equipos_by_cliente_nombre(db: Session, nombre: str) -> List[Equipo]:
    stmt = select(Equipo).join(Cliente).where(Cliente.nombre_completo.ilike(f"%{nombre}%"))
    stmt = stmt.order_by(Equipo.fecha_ingreso.desc())
    return list(db.execute(stmt).scalars())

# 🔹 Actualizar equipo
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
    if payload.estado is not None and payload.estado in VALID_ESTADOS:
        obj.estado = payload.estado

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

# 🔹 Eliminar equipo
def delete_equipo(db: Session, equipo_id: int) -> bool:
    obj = db.get(Equipo, equipo_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True



# 🔹 Guardar URL del QR en el equipo
def set_equipo_qr(db: Session, equipo_id: int, qr_url: str) -> Optional[Equipo]:
    obj = db.query(Equipo).filter(Equipo.id == equipo_id).first()
    if not obj:
        return None
    obj.qr_url = qr_url
    db.commit()
    db.refresh(obj)
    return obj


# 🔹 Subir foto del equipo
def set_equipo_foto(db: Session, equipo_id: int, foto_url: str) -> Optional[Equipo]:
    obj = db.get(Equipo, equipo_id)
    if not obj:
        return None
    obj.foto_url = foto_url
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
