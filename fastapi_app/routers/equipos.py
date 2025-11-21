import uuid
import json
from pathlib import Path
from typing import List, Optional

import qrcode
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from schemas.equipo import EquipoCreate, EquipoUpdate, EquipoOut
from crud import equipo as crud_equipos

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
# 🚀 CREAR EQUIPO (con cliente automático si no mandas cliente_id)
# =====================================================
@router.post("/", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(payload: EquipoCreate, db: Session = Depends(get_db)):
    equipo = crud_equipos.create_equipo(db, payload)
    if not equipo:
        raise HTTPException(status_code=400, detail="No se pudo crear el equipo")

    # Generar QR con el ID del equipo
    qr_data = str(equipo.id)
    qr_img = qrcode.make(qr_data)
    qr_filename = f"{uuid.uuid4().hex}.png"
    qr_path = QR_DIR / qr_filename
    qr_img.save(qr_path)
    qr_url = f"/static/qrs/equipos/{qr_filename}"

    equipo = crud_equipos.set_equipo_qr(db, equipo.id, qr_url)
    return equipo


# =====================================================
# 🔍 LISTAR EQUIPOS
# =====================================================
@router.get("/", response_model=List[EquipoOut])
def listar_equipos(
    nombre_cliente: Optional[str] = Query(None, description="Buscar por nombre de cliente"),
    estado: Optional[str] = Query(None, description="Estado del equipo"),
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
# 📸 SUBIR FOTO DEL EQUIPO (un solo archivo para equipo específico)
# =====================================================
@router.post("/{equipo_id}/foto", response_model=EquipoOut)
async def subir_foto_equipo(
    equipo_id: int,
    file: UploadFile = File(..., description="Imagen del equipo en recepción"),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen")

    suffix = Path(file.filename).suffix.lower() if file.filename else ""
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Usa JPG, PNG o WEBP"
        )

    filename = f"{uuid.uuid4().hex}{suffix}"
    out_path = UPLOAD_DIR / filename

    try:
        with open(out_path, "wb") as f:
            f.write(await file.read())

        foto_url = f"/static/uploads/equipos/{filename}"
        obj = crud_equipos.set_equipo_foto(db, equipo_id, foto_url)
        if not obj:
            out_path.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="Equipo no encontrado")
        return obj
    except HTTPException:
        raise
    except Exception as e:
        try:
            out_path.unlink(missing_ok=True)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error guardando la imagen: {str(e)}")


# =====================================================
# 📸 SUBIR DOS FOTOS (front + back) AL ÚLTIMO EQUIPO CREADO
# =====================================================
@router.post("/fotos/ultimo", response_model=EquipoOut, status_code=status.HTTP_200_OK)
async def subir_fotos_ultimo(
    front: UploadFile = File(..., description="Foto frontal"),
    back: UploadFile = File(..., description="Foto trasera"),
    db: Session = Depends(get_db),
):
    # Validar que sean imágenes y extensiones permitidas
    for f in (front, back):
        if not f.content_type or not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Los archivos deben ser imágenes")
        suffix = Path(f.filename).suffix.lower() if f.filename else ""
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise HTTPException(status_code=400, detail="Formato inválido. Usa JPG, PNG o WEBP")

    saved_files = []
    try:
        # Guardar front
        front_suffix = Path(front.filename).suffix.lower()
        front_name = f"{uuid.uuid4().hex}{front_suffix}"
        front_path = UPLOAD_DIR / front_name
        with open(front_path, "wb") as out_f:
            out_f.write(await front.read())
        front_url = f"/static/uploads/equipos/{front_name}"
        saved_files.append(front_path)

        # Guardar back
        back_suffix = Path(back.filename).suffix.lower()
        back_name = f"{uuid.uuid4().hex}{back_suffix}"
        back_path = UPLOAD_DIR / back_name
        with open(back_path, "wb") as out_f:
            out_f.write(await back.read())
        back_url = f"/static/uploads/equipos/{back_name}"
        saved_files.append(back_path)

        # Obtener último equipo
        ultimo = crud_equipos.get_last_equipo(db)
        if not ultimo:
            for p in saved_files:
                p.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="No se encontró ningún equipo existente")

        # Guardar las dos fotos como JSON en el campo foto_url
        fotos_json = json.dumps({"front": front_url, "back": back_url})
        actualizado = crud_equipos.set_equipo_foto_json(db, ultimo.id, fotos_json)
        if not actualizado:
            # limpiar archivos guardados
            for p in saved_files:
                p.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="Error guardando las fotos en el equipo")

        return actualizado

    except HTTPException:
        raise
    except Exception as e:
        for p in saved_files:
            try:
                p.unlink(missing_ok=True)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error guardando las imágenes: {str(e)}")
