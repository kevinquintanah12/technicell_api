# routers/equipos.py
import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi import status
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from schemas.equipo import EquipoCreate, EquipoUpdate, EquipoOut
from crud.equipos import (
    create_equipo, list_equipos, get_equipo, update_equipo, delete_equipo, set_equipo_foto
)

# Asegura que las tablas existan al importar el router (si no usas Alembic)
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/equipos", tags=["Equipos"])

# Carpeta para fotos
UPLOAD_DIR = Path("static/uploads/equipos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(payload: EquipoCreate, db: Session = Depends(get_db)):
    # Validaciones simples (Pydantic ya exige modelo/fallo)
    obj = create_equipo(db, payload)
    return obj

@router.get("/", response_model=List[EquipoOut])
def listar_equipos(
    cliente_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None, description="Estado del equipo para filtrar"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return list_equipos(db, skip=skip, limit=limit, cliente_id=cliente_id, estado=estado)

@router.get("/{equipo_id}", response_model=EquipoOut)
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = get_equipo(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj

@router.patch("/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(equipo_id: int, payload: EquipoUpdate, db: Session = Depends(get_db)):
    obj = update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj

@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    ok = delete_equipo(db, equipo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return None

@router.post("/{equipo_id}/foto", response_model=EquipoOut)
async def subir_foto_equipo(
    equipo_id: int,
    file: UploadFile = File(..., description="Imagen del equipo en recepción"),
    db: Session = Depends(get_db),
):
    # Validar tipo MIME
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    # Extensión
    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Formato inválido. Usa JPG, PNG o WEBP")

    # Nombre único
    out_name = f"{uuid.uuid4().hex}{suffix}"
    out_path = UPLOAD_DIR / out_name

    # Guardar a disco
    with open(out_path, "wb") as f:
        f.write(await file.read())

    # URL pública (serviremos /static en main.py)
    foto_url = f"/static/uploads/equipos/{out_name}"

    obj = set_equipo_foto(db, equipo_id, foto_url)
    if not obj:
        # Limpia archivo si el equipo no existe
        try:
            out_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    return obj
