from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from crud.client import create_client, get_clients, get_client, update_client, delete_client
from schemas.client import ClientCreate, ClientUpdate, ClientOut  # import absoluto

router = APIRouter(prefix="/clientes", tags=["Clientes"])


# 🔹 Dependencia de sesión DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔹 Crear cliente
@router.post("/", response_model=ClientOut)
def create_client_endpoint(client: ClientCreate, db: Session = Depends(get_db)):
    return create_client(db, client)


# 🔹 Listar clientes con búsqueda opcional por nombre
@router.get("/", response_model=list[ClientOut])
def list_clients_endpoint(
    skip: int = 0,
    limit: int = 100,
    nombre: str | None = Query(None, description="Buscar clientes por nombre parcial"),
    db: Session = Depends(get_db)
):
    return get_clients(db, skip=skip, limit=limit, nombre=nombre)


# 🔹 Obtener un cliente específico
@router.get("/{client_id}", response_model=ClientOut)
def get_client_endpoint(client_id: int, db: Session = Depends(get_db)):
    db_client = get_client(db, client_id)
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return db_client


# 🔹 Actualizar cliente
@router.put("/{client_id}", response_model=ClientOut)
def update_client_endpoint(client_id: int, update: ClientUpdate, db: Session = Depends(get_db)):
    db_client = update_client(db, client_id, update)
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return db_client


# 🔹 Eliminar cliente
@router.delete("/{client_id}")
def delete_client_endpoint(client_id: int, db: Session = Depends(get_db)):
    result = delete_client(db, client_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"detail": "Cliente eliminado correctamente"}
