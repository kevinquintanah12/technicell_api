from sqlalchemy.orm import Session
from sqlalchemy import select
from models.client import Cliente  # clase SQLAlchemy correcta
from schemas import ClientCreate, ClientUpdate  # Pydantic schemas
from typing import List, Optional

def create_client(db: Session, client: ClientCreate):
    db_client = Cliente(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

# 🔹 Listar clientes con búsqueda flexible
def get_clients(db: Session, skip: int = 0, limit: int = 100, nombre: Optional[str] = None) -> List[Cliente]:
    stmt = select(Cliente)
    if nombre:
        # Coincidencia parcial, case-insensitive
        stmt = stmt.where(Cliente.nombre_completo.ilike(f"%{nombre}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.execute(stmt).scalars())

def get_client(db: Session, client_id: int):
    return db.query(Cliente).filter(Cliente.id == client_id).first()

def update_client(db: Session, client_id: int, update_data: ClientUpdate):
    client = get_client(db, client_id)
    if client:
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(client, key, value)
        db.commit()
        db.refresh(client)
    return client

def delete_client(db: Session, client_id: int):
    client = get_client(db, client_id)
    if client:
        db.delete(client)
        db.commit()
    return client
