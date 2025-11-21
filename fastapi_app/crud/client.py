# crud/cliente.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from models.client import Cliente
from schemas.client import ClientCreate, ClientUpdate


# ---------------------------------------------------------
# 🔹 Crear cliente
# ---------------------------------------------------------
def create_client(db: Session, client_data: ClientCreate) -> Cliente:
    db_client = Cliente(**client_data.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


# ---------------------------------------------------------
# 🔹 Obtener cliente por ID
# ---------------------------------------------------------
def get_client_by_id(db: Session, client_id: int) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.id == client_id).first()


# ---------------------------------------------------------
# 🔹 Obtener cliente por teléfono (único)
# ---------------------------------------------------------
def get_client_by_phone(db: Session, telefono: str) -> Optional[Cliente]:
    return db.query(Cliente).filter(Cliente.telefono == telefono).first()


# ---------------------------------------------------------
# 🔹 Obtener o crear cliente automáticamente
# ---------------------------------------------------------
def get_or_create_client(
    db: Session,
    nombre: str,
    telefono: str,
    correo: Optional[str]
) -> Cliente:

    # 1) Buscar cliente por teléfono
    cliente = get_client_by_phone(db, telefono)

    if cliente:
        return cliente

    # 2) Crear cliente si no existe
    nuevo_cliente = Cliente(
        nombre_completo=nombre,
        telefono=telefono,
        correo=correo
    )

    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)

    return nuevo_cliente


# ---------------------------------------------------------
# 🔹 Obtener lista de clientes
# ---------------------------------------------------------
def get_clients(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    nombre: Optional[str] = None,
) -> List[Cliente]:

    stmt = select(Cliente)

    if nombre:
        stmt = stmt.where(Cliente.nombre_completo.ilike(f"%{nombre}%"))

    stmt = stmt.offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


# ---------------------------------------------------------
# 🔹 Actualizar cliente
# ---------------------------------------------------------
def update_client(db: Session, client_id: int, update_data: ClientUpdate) -> Optional[Cliente]:
    client = get_client_by_id(db, client_id)
    if not client:
        return None

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(client, key, value)

    db.commit()
    db.refresh(client)
    return client


# ---------------------------------------------------------
# 🔹 Eliminar cliente
# ---------------------------------------------------------
def delete_client(db: Session, client_id: int) -> Optional[Cliente]:
    client = get_client_by_id(db, client_id)
    if not client:
        return None

    db.delete(client)
    db.commit()
    return client
