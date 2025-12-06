import uuid
import json
from pathlib import Path
from typing import List, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from schemas.equipo import EquipoCreate, EquipoUpdate, EquipoOut
from crud import equipos as crud_equipos

# Crear tablas (si no las creaste en otro lugar)
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/equipos", tags=["Equipos"])

# Carpetas para fotos y QRs
UPLOAD_DIR = Path("static/uploads/equipos")
QR_DIR = Path("static/qrs/equipos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
QR_DIR.mkdir(parents=True, exist_ok=True)


# Dependencia DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================
# 🚀 CREAR EQUIPO
# =====================================================
@router.post("/", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(payload: EquipoCreate, db: Session = Depends(get_db)):
    equipo = crud_equipos.create_equipo(db, payload)
    if not equipo:
        raise HTTPException(status_code=400, detail="No se pudo crear el equipo")

    # Generar QR
    qr_filename = f"{uuid.uuid4().hex}.png"
    qr_path = QR_DIR / qr_filename
    qrcode.make(str(equipo.id)).save(qr_path)
    qr_url = f"/static/qrs/equipos/{qr_filename}"

    return crud_equipos.set_equipo_qr(db, equipo.id, qr_url)


# =====================================================
# 🔍 LISTAR EQUIPOS
# =====================================================
@router.get("/", response_model=List[EquipoOut])
def listar_equipos(
    nombre_cliente: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    if nombre_cliente:
        return crud_equipos.get_equipos_by_cliente_nombre(db, nombre_cliente)

    return crud_equipos.list_equipos(
        db,
        skip=skip,
        limit=limit,
        cliente_nombre=nombre_cliente,
        estado=estado,
    )


# =====================================================
# 🔍 OBTENER EQUIPO POR ID
# =====================================================
@router.get("/{equipo_id}", response_model=EquipoOut)
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = crud_equipos.get_equipo(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# =====================================================
# ✏️ ACTUALIZAR EQUIPO
# =====================================================
@router.patch("/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(equipo_id: int, payload: EquipoUpdate, db: Session = Depends(get_db)):
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# =====================================================
# 🗑️ ELIMINAR EQUIPO
# =====================================================
@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    ok = crud_equipos.delete_equipo(db, equipo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return None


# =====================================================
# 📸 SUBIR FOTO — 1 FOTO A UN EQUIPO ESPECÍFICO
# =====================================================
@router.post("/{equipo_id}/foto", response_model=EquipoOut)
async def subir_foto_equipo(
    equipo_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="Formato inválido")

    filename = f"{uuid.uuid4().hex}{ext}"
    path = UPLOAD_DIR / filename

    try:
        with open(path, "wb") as f:
            f.write(await file.read())

        url = f"/static/uploads/equipos/{filename}"
        res = crud_equipos.set_equipo_foto(db, equipo_id, url)

        if not res:
            path.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="Equipo no encontrado")

        return res

    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 📸 SUBIR **DOS FOTOS** (FRONT + BACK) AL ÚLTIMO EQUIPO
# =====================================================
@router.post("/fotos/ultimo", response_model=EquipoOut)
async def subir_fotos_ultimo(
    front: UploadFile = File(...),
    back: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    for f in (front, back):
        if not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Ambos archivos deben ser imágenes")

        ext = Path(f.filename).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Formato inválido")

    saved = []

    try:
        # FRONT
        ext_front = Path(front.filename).suffix.lower()
        name_front = f"{uuid.uuid4().hex}{ext_front}"
        path_front = UPLOAD_DIR / name_front
        with open(path_front, "wb") as f:
            f.write(await front.read())
        url_front = f"/static/uploads/equipos/{name_front}"
        saved.append(path_front)

        # BACK
        ext_back = Path(back.filename).suffix.lower()
        name_back = f"{uuid.uuid4().hex}{ext_back}"
        path_back = UPLOAD_DIR / name_back
        with open(path_back, "wb") as f:
            f.write(await back.read())
        url_back = f"/static/uploads/equipos/{name_back}"
        saved.append(path_back)

        # OBTENER ÚLTIMO EQUIPO
        ultimo = crud_equipos.get_last_equipo(db)
        if not ultimo:
            for p in saved:
                p.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="No hay equipos registrados")

        # GUARDAR JSON EN BD
        json_fotos = json.dumps({"front": url_front, "back": url_back})
        actualizado = crud_equipos.set_equipo_foto_json(db, ultimo.id, json_fotos)

        if not actualizado:
            for p in saved:
                p.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="Error guardando fotos")

        return actualizado

    except Exception as e:
        for p in saved:
            p.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))
