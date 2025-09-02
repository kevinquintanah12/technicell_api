from sqlalchemy.orm import Session
from ..models.client import Client  # <- importar la clase directamente
from .. import schemas

def create_client(db: Session, client: schemas.ClientCreate):
    db_client = Client(**client.dict())  # <- usar Client directamente
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def get_clients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Client).offset(skip).limit(limit).all()

def get_client(db: Session, client_id: int):
    return db.query(Client).filter(Client.id == client_id).first()

def update_client(db: Session, client_id: int, update_data: schemas.ClientUpdate):
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
