# crud/equipo.py
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from models.equipo import Equipo
from schemas.equipo import EquipoCreate, EquipoUpdate
from crud.client import get_or_create_client

VALID_ESTADOS = [
    "recibido",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado"
]


# ---------------------------------------------------------
# 🔹 Crear equipo (auto crea cliente si no existe)
# ---------------------------------------------------------
def create_equipo(db: Session, payload: EquipoCreate) -> Equipo:
    # 1) Obtener o crear cliente automáticamente
    cliente = get_or_create_client(
        db=db,
        nombre=payload.cliente_nombre,
        telefono=payload.cliente_numero,
        correo=payload.cliente_correo
    )

    # 2) Validar estado
    estado = payload.estado if payload.estado in VALID_ESTADOS else "recibido"

    # 3) Crear equipo
    db_equipo = Equipo(
        cliente_nombre=cliente.nombre_completo,
        cliente_numero=cliente.telefono,
        cliente_correo=cliente.correo,

        marca=payload.marca,
        modelo=payload.modelo,
        fallo=payload.fallo,
        observaciones=payload.observaciones,
        clave_bloqueo=payload.clave_bloqueo,
        articulos_entregados=payload.articulos_entregados or [],
        estado=estado,
        imei=payload.imei,
        fecha_ingreso=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    db.add(db_equipo)
    db.commit()
    db.refresh(db_equipo)
    return db_equipo


# ---------------------------------------------------------
# 🔹 Obtener equipo por ID
# ---------------------------------------------------------
def get_equipo(db: Session, equipo_id: int) -> Optional[Equipo]:
    return db.get(Equipo, equipo_id)


# ---------------------------------------------------------
# 🔹 Listar equipos con filtros
# ---------------------------------------------------------
def list_equipos(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    cliente_nombre: Optional[str] = None,
    estado: Optional[str] = None,
) -> List[Equipo]:

    stmt = select(Equipo)

    if cliente_nombre:
        stmt = stmt.where(Equipo.cliente_nombre.ilike(f"%{cliente_nombre}%"))

    if estado:
        if estado in VALID_ESTADOS:
            stmt = stmt.where(Equipo.estado == estado)
        else:
            stmt = stmt.where(Equipo.id == -1)

    stmt = stmt.order_by(Equipo.fecha_ingreso.desc()).offset(skip).limit(limit)

    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------
# 🔹 Buscar equipos por nombre del cliente
# ---------------------------------------------------------
def get_equipos_by_cliente_nombre(db: Session, nombre: str) -> List[Equipo]:
    stmt = select(Equipo).where(Equipo.cliente_nombre.ilike(f"%{nombre}%"))
    stmt = stmt.order_by(Equipo.fecha_ingreso.desc())
    return list(db.execute(stmt).scalars())


# ---------------------------------------------------------
# 🔹 Actualizar equipo
# ---------------------------------------------------------
def update_equipo(db: Session, equipo_id: int, payload: EquipoUpdate) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    for key, value in payload.dict(exclude_unset=True).items():
        if key == "estado" and value not in VALID_ESTADOS:
            continue
        setattr(equipo, key, value)

    db.commit()
    db.refresh(equipo)
    return equipo


# ---------------------------------------------------------
# 🔹 Eliminar equipo
# ---------------------------------------------------------
def delete_equipo(db: Session, equipo_id: int) -> bool:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return False

    db.delete(equipo)
    db.commit()
    return True


# ---------------------------------------------------------
# 🔹 Guardar URL del QR
# ---------------------------------------------------------
def set_equipo_qr(db: Session, equipo_id: int, qr_url: str) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    equipo.qr_url = qr_url
    db.commit()
    db.refresh(equipo)
    return equipo


# ---------------------------------------------------------
# 🔹 Guardar foto del equipo
# ---------------------------------------------------------
def set_equipo_foto(db: Session, equipo_id: int, foto_url: str) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    equipo.foto_url = foto_url
    db.commit()
    db.refresh(equipo)
    return equipo
