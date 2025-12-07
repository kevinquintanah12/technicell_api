from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
import json

from models.equipo import Equipo
from schemas.equipo import EquipoCreate, EquipoUpdate
from crud.client import get_or_create_client

# Estados válidos
VALID_ESTADOS = [
    "recibido",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado",
    "pendientes"  # 👈 agregado
]

# =====================================================
# 🔹 Crear equipo (crea cliente si no existe)
# =====================================================
def create_equipo(db: Session, payload: EquipoCreate) -> Equipo:
    cliente = get_or_create_client(
        db=db,
        nombre=payload.cliente_nombre,
        telefono=payload.cliente_numero,
        correo=payload.cliente_correo
    )

    estado = payload.estado if payload.estado in VALID_ESTADOS else "pendientes"

    db_equipo = Equipo(
        cliente_id=cliente.id,
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
        fecha_ingreso=datetime.now()
    )

    db.add(db_equipo)
    db.commit()
    db.refresh(db_equipo)

    return db_equipo


# =====================================================
# 🔹 Obtener equipo por ID
# =====================================================
def get_equipo(db: Session, equipo_id: int) -> Optional[Equipo]:
    return db.get(Equipo, equipo_id)


# =====================================================
# 🔹 Listar equipos con filtros
# =====================================================
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


# =====================================================
# 🔹 Buscar por nombre del cliente
# =====================================================
def get_equipos_by_cliente_nombre(db: Session, nombre: str) -> List[Equipo]:
    stmt = select(Equipo).where(Equipo.cliente_nombre.ilike(f"%{nombre}%"))
    stmt = stmt.order_by(Equipo.fecha_ingreso.desc())
    return list(db.execute(stmt).scalars())


# =====================================================
# 🔹 Actualizar equipo
# =====================================================
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


# =====================================================
# 🔹 Borrar equipo
# =====================================================
def delete_equipo(db: Session, equipo_id: int) -> bool:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return False

    db.delete(equipo)
    db.commit()
    return True


# =====================================================
# 🔹 Guardar QR
# =====================================================
def set_equipo_qr(db: Session, equipo_id: int, qr_url: str) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    equipo.qr_url = qr_url
    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Guardar foto única
# =====================================================
def set_equipo_foto(db: Session, equipo_id: int, foto_url: str) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    equipo.foto_url = foto_url
    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Obtener último equipo creado
# =====================================================
def get_last_equipo(db: Session) -> Optional[Equipo]:
    stmt = select(Equipo).order_by(Equipo.id.desc()).limit(1)
    return db.execute(stmt).scalars().first()


# =====================================================
# 🔹 Guardar JSON con front + back
# =====================================================
def set_equipo_foto_json(db: Session, equipo_id: int, fotos_json: str) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    try:
        parsed = json.loads(fotos_json)
        if not isinstance(parsed, dict):
            raise ValueError("JSON inválido")
        equipo.foto_url = json.dumps(parsed)
    except Exception:
        equipo.foto_url = fotos_json

    db.commit()
    db.refresh(equipo)
    return equipo
