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
    "recibido",
    "diagnostico",
    "en_reparacion",
    "listo",
    "entregado",
    "cancelado",
    "pendientes",
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
def list_equipos(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    cliente_nombre: Optional[str] = None,
    estado: Optional[str] = None,
) -> List[Equipo]:

    stmt = select(Equipo).where(Equipo.archived == False)

    if cliente_nombre:
        stmt = stmt.where(
            Equipo.cliente_nombre.ilike(f"%{cliente_nombre}%")
        )

    if estado:
        if estado in VALID_ESTADOS:
            stmt = stmt.where(Equipo.estado == estado)
        else:
            # estado inválido → no retorna nada
            stmt = stmt.where(Equipo.id == -1)

    stmt = (
        stmt.order_by(Equipo.fecha_ingreso.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.execute(stmt).scalars())


# =====================================================
# 🔹 Buscar equipos activos por nombre de cliente
# =====================================================
def get_equipos_by_cliente_nombre(
    db: Session, nombre: str
) -> List[Equipo]:

    stmt = (
        select(Equipo)
        .where(
            Equipo.archived == False,
            Equipo.cliente_nombre.ilike(f"%{nombre}%"),
        )
        .order_by(Equipo.fecha_ingreso.desc())
    )

    return list(db.execute(stmt).scalars())


# =====================================================
# 🔹 Actualizar equipo
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
# 🔹 Marcar equipo como LISTO (🔥 CLAVE 🔥)
# =====================================================
def marcar_equipo_listo(
    db: Session,
    equipo_id: int,
    archivar: bool = True,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    equipo.estado = "listo"
    equipo.fecha_entrega = datetime.utcnow()

    if archivar:
        equipo.archived = True

    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Cancelar equipo (también se archiva)
# =====================================================
def cancelar_equipo(db: Session, equipo_id: int) -> Optional[Equipo]:
    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    equipo.estado = "cancelado"
    equipo.archived = True
    equipo.fecha_entrega = datetime.utcnow()

    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Borrado lógico (NO se elimina de BD)
# =====================================================
def delete_equipo(db: Session, equipo_id: int) -> bool:
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


# =====================================================
# 🔹 Guardar foto (URL simple)
# =====================================================
def set_equipo_foto(
    db: Session,
    equipo_id: int,
    foto_url: str,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    equipo.foto_url = foto_url
    db.commit()
    db.refresh(equipo)
    return equipo


# =====================================================
# 🔹 Obtener último equipo ACTIVO
# =====================================================
def get_last_equipo(db: Session) -> Optional[Equipo]:
    stmt = (
        select(Equipo)
        .where(Equipo.archived == False)
        .order_by(Equipo.id.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


# =====================================================
# 🔹 Guardar JSON de fotos (front + back)
# =====================================================
def set_equipo_foto_json(
    db: Session,
    equipo_id: int,
    fotos_json: str,
) -> Optional[Equipo]:

    equipo = db.get(Equipo, equipo_id)
    if not equipo or equipo.archived:
        return None

    try:
        parsed = json.loads(fotos_json)
        if not isinstance(parsed, dict):
            raise ValueError("JSON inválido")
        equipo.foto_url = json.dumps(parsed)
    except Exception:
        # fallback: guardar texto plano
        equipo.foto_url = fotos_json

    db.commit()
    db.refresh(equipo)
    return equipo
