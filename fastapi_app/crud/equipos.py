from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
import json

from models.equipo import Equipo
from schemas.equipo import EquipoCreate, EquipoUpdate
from crud.client import get_or_create_client


# ==========================
# ESTADOS VÁLIDOS
# ==========================
VALID_ESTADOS = [
    "pendientes",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado",
]


# =====================================================
# 🔹 Crear equipo (crea cliente si no existe)
# =====================================================
def create_equipo(db: Session, payload: EquipoCreate) -> Equipo:
    cliente = get_or_create_client(
        db=db,
        nombre=payload.cliente_nombre,
        telefono=payload.cliente_numero,
        correo=payload.cliente_correo,
    )

    estado = payload.estado if payload.estado in VALID_ESTADOS else "pendientes"

    db_equipo = Equipo(
        # ---- CLIENTE ----
        cliente_id=cliente.id,
        cliente_nombre=cliente.nombre_completo,
        cliente_numero=cliente.telefono,
        cliente_correo=cliente.correo,

        # ---- EQUIPO ----
        marca=payload.marca,
        modelo=payload.modelo,
        fallo=payload.fallo,
        observaciones=payload.observaciones,

        # ---- SEGURIDAD ----
        tipo_clave=payload.tipo_clave,
        clave_bloqueo=payload.clave_bloqueo,

        # ---- OTROS ----
        articulos_entregados=payload.articulos_entregados or [],
        estado=estado,
        imei=payload.imei,

        fecha_ingreso=datetime.utcnow(),
        archived=False,
    )

    db.add(db_equipo)
    db.commit()
    db.refresh(db_equipo)
    return db_equipo


# =====================================================
# 🔹 Obtener equipo por ID (incluye archivados)
# =====================================================
def get_equipo(db: Session, equipo_id: int) -> Optional[Equipo]:
    return db.get(Equipo, equipo_id)


# =====================================================
# 🔹 Listar equipos ACTIVOS (NO archivados)
# =====================================================
def list_equipos_activos(db: Session) -> List[Equipo]:
    stmt = (
        select(Equipo)
        .where(Equipo.archived == False)
        .order_by(Equipo.fecha_ingreso.desc())
    )
    return list(db.execute(stmt).scalars())


# =====================================================
# 🔹 Listar equipos por estado (NO archivados)
# =====================================================
def list_equipos_por_estado(
    db: Session,
    estado: str,
) -> List[Equipo]:

    if estado not in VALID_ESTADOS:
        return []

    stmt = (
        select(Equipo)
        .where(
            Equipo.archived == False,
            Equipo.estado == estado,
        )
        .order_by(Equipo.fecha_ingreso.desc())
    )

    return list(db.execute(stmt).scalars())


# =====================================================
# 🔹 LISTAR POR ESTADO (INCLUYE ARCHIVADOS) 🔥
# =====================================================
def list_equipos_por_estado_incluyendo_archivados(
    db: Session,
    estado: str,
) -> List[Equipo]:

    if estado not in VALID_ESTADOS:
        return []

    stmt = (
        select(Equipo)
        .where(Equipo.estado == estado)
        .order_by(Equipo.fecha_ingreso.desc())
    )

    return list(db.execute(stmt).scalars())


# =====================================================
# 🔹 Actualizar equipo (NO ARCHIVADOS)
# =====================================================
def update_equipo(
    db: Session,
    equipo_id: int,
    payload: EquipoUpdate,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    for key, value in payload.dict(exclude_unset=True).items():
        if key == "estado" and value not in VALID_ESTADOS:
            continue
        setattr(equipo, key, value)

    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 ENTREGAR EQUIPO (ARCHIVA) 🔥🔥🔥
# =====================================================
def marcar_equipo_entregado(
    db: Session,
    equipo_id: int,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return None

    equipo.estado = "entregado"
    equipo.archived = True
    equipo.fecha_entrega = datetime.utcnow()

    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Cancelar equipo (NO archiva por defecto)
# =====================================================
def cancelar_equipo(
    db: Session,
    equipo_id: int,
    archivar: bool = False,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    equipo.estado = "cancelado"

    if archivar:
        equipo.archived = True
        equipo.fecha_entrega = datetime.utcnow()

    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Archivado manual
# =====================================================
def archivar_equipo(db: Session, equipo_id: int) -> bool:
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        return False

    equipo.archived = True
    db.commit()
    return True


# =====================================================
# 🔹 Guardar QR
# =====================================================
def set_equipo_qr(
    db: Session,
    equipo_id: int,
    qr_url: str,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    equipo.qr_url = qr_url
    db.commit()
    db.refresh(equipo)
    return equipo

