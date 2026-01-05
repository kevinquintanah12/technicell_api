from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import SessionLocal
from crud.client import (
    create_client,
    get_clients,
    get_client_by_id,
    update_client,
    delete_client,
)
from schemas.client import ClientCreate, ClientUpdate, ClientOut

router = APIRouter(
    prefix="/clientes",
    tags=["Clientes"]
)

# ---------------------------
# Dependencia DB
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# Crear cliente
# ---------------------------
@router.post("/", response_model=ClientOut, status_code=201)
def create_client_endpoint(
    client: ClientCreate,
    db: Session = Depends(get_db)
):
    return create_client(db, client)


# ---------------------------
# Mostrar / listar clientes
# ---------------------------
@router.get("/", response_model=List[ClientOut])
def list_clients_endpoint(
    skip: int = Query(0, ge=0, description="Registros a omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad de registros"),
    nombre: Optional[str] = Query(
        None,
        description="Buscar clientes por nombre (parcial)"
    ),
    db: Session = Depends(get_db),
):
    """
    Lista clientes con paginación y búsqueda por nombre.
    Ideal para tablas, dashboards y buscadores.
    """
    return get_clients(
        db,
        skip=skip,
        limit=limit,
        nombre=nombre,
    )


# ---------------------------
# Obtener cliente por ID
# ---------------------------
@router.get("/{client_id}", response_model=ClientOut)
def get_client_endpoint(
    client_id: int,
    db: Session = Depends(get_db)
):
    client = get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )
    return client


# ---------------------------
# Actualizar cliente
# ---------------------------
@router.put("/{client_id}", response_model=ClientOut)
def update_client_endpoint(
    client_id: int,
    update: ClientUpdate,
    db: Session = Depends(get_db)
):
    client = update_client(db, client_id, update)
    if not client:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )
    return client


# ---------------------------
# Eliminar cliente
# ---------------------------
@router.delete("/{client_id}", status_code=200)
def delete_client_endpoint(
    client_id: int,
    db: Session = Depends(get_db)
):
    deleted = delete_client(db, client_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado"
        )
    return {"detail": "Cliente eliminado correctamente"}
