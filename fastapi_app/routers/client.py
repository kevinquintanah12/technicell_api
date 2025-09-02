from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..crud import client as crud_client  # <- importar el módulo client.py
from .. import schemas

router = APIRouter(prefix="/clientes", tags=["Clientes"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.ClientOut)
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db)):
    return crud_client.create_client(db, client)

@router.get("/", response_model=list[schemas.ClientOut])
def list_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_client.get_clients(db, skip=skip, limit=limit)

@router.get("/{client_id}", response_model=schemas.ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db)):
    db_client = crud_client.get_client(db, client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return db_client

@router.put("/{client_id}", response_model=schemas.ClientOut)
def update_client(client_id: int, update: schemas.ClientUpdate, db: Session = Depends(get_db)):
    return crud_client.update_client(db, client_id, update)

@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    return crud_client.delete_client(db, client_id)
