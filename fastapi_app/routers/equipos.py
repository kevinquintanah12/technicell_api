# equipos_router.py
"""
Router completo para /equipos con:
- creación de equipos (genera QR)
- listar, filtros y cambios de estado
- subir fotos al último equipo
- notificaciones por email
- endpoints para decodificar QR (archivo multipart y base64)

Requiere:
pip install pillow opencv-python-headless qrcode
"""

import uuid
import json
import io
import base64
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from PIL import Image, ImageOps
import numpy as np
import cv2

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query,
    status,
    Request,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from services.email_equipo import enviar_email_reparacion
from schemas.equipo import (
    EquipoCreate,
    EquipoUpdate,
    EquipoOut,
    EquipoNotificar,
)
from crud import equipos as crud_equipos

# ==========================
# CREAR TABLAS (solo si no lo haces en otro lado)
# ==========================
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/equipos", tags=["Equipos"])

# =====================================================
# 📂 DIRECTORIOS
# =====================================================
UPLOAD_DIR = Path("static/uploads/equipos")
QR_DIR = Path("static/qrs/equipos")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
QR_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# 🗄️ DB
# =====================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def absolute_url(request: Request, relative_path: str) -> str:
    base = str(request.base_url).rstrip("/")
    rel = relative_path if relative_path.startswith("/") else f"/{relative_path}"
    return f"{base}{rel}"


# =====================================================
# ⚙️ CONFIG
# =====================================================
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

# =====================================================
# 🔧 OpenCV QR
# =====================================================
_detector = cv2.QRCodeDetector()


def pil_to_cv2_bgr(pil_image: Image.Image) -> np.ndarray:
    rgb = np.array(pil_image.convert("RGB"))
    return rgb[:, :, ::-1].copy()


def try_decode_qr(pil_image: Image.Image) -> Optional[str]:
    candidates: List[Image.Image] = []

    try:
        candidates.append(pil_image.convert("RGB"))
        candidates.append(ImageOps.autocontrast(pil_image))
        candidates.append(ImageOps.grayscale(pil_image))
    except Exception:
        pass

    for base_img in candidates[:]:
        for rot in (90, 180, 270):
            try:
                candidates.append(base_img.rotate(rot, expand=True))
            except Exception:
                pass

    for img in candidates:
        try:
            cv_img = pil_to_cv2_bgr(img)
            data, _, _ = _detector.detectAndDecode(cv_img)
            if data and data.strip():
                return data.strip()
        except Exception:
            continue

    return None


# =====================================================
# 🚀 CREAR EQUIPO + QR
# =====================================================
@router.post("/", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(
    payload: EquipoCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    equipo = crud_equipos.create_equipo(db, payload)
    if not equipo:
        raise HTTPException(status_code=400, detail="No se pudo crear el equipo")

    import qrcode

    qr_filename = f"{uuid.uuid4().hex}.png"
    qr_path = QR_DIR / qr_filename

    img_qr = qrcode.make(str(equipo.id))
    img_qr.save(qr_path)

    qr_url = absolute_url(request, f"/static/qrs/equipos/{qr_filename}")

    updated = crud_equipos.set_equipo_qr(db, equipo.id, qr_url)
    if not updated:
        raise HTTPException(status_code=500, detail="No se pudo guardar QR")

    return updated


# =====================================================
# 🔍 LISTAR EQUIPOS ACTIVOS
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
        db=db,
        skip=skip,
        limit=limit,
        cliente_nombre=nombre_cliente,
        estado=estado,
    )


# =====================================================
# ⚡ FILTROS RÁPIDOS
# =====================================================
@router.get("/pendientes", response_model=List[EquipoOut])
def equipos_pendientes(db: Session = Depends(get_db)):
    return crud_equipos.list_equipos(db, estado="pendientes")


@router.get("/reparacion", response_model=List[EquipoOut])
def equipos_reparacion(db: Session = Depends(get_db)):
    return crud_equipos.list_equipos(db, estado="en_reparacion")


# =====================================================
# 📸 SUBIR FOTOS AL ÚLTIMO EQUIPO
# =====================================================
@router.post("/fotos/ultimo", response_model=EquipoOut)
async def subir_fotos_ultimo(
    request: Request,
    front: UploadFile = File(...),
    back: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    for f in (front, back):
        if not f.content_type or not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Archivos inválidos")

    try:
        def save_image(file: UploadFile) -> str:
            ext = Path(file.filename).suffix or ".jpg"
            name = f"{uuid.uuid4().hex}{ext}"
            path = UPLOAD_DIR / name
            with open(path, "wb") as fh:
                fh.write(file.file.read())
            return absolute_url(request, f"/static/uploads/equipos/{name}")

        url_front = save_image(front)
        url_back = save_image(back)

        ultimo = crud_equipos.get_last_equipo(db)
        if not ultimo:
            raise HTTPException(status_code=404, detail="No hay equipos")

        fotos_json = json.dumps({"front": url_front, "back": url_back})
        updated = crud_equipos.set_equipo_foto_json(db, ultimo.id, fotos_json)

        return updated

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🔄 CAMBIOS DE ESTADO
# =====================================================
@router.patch("/{equipo_id}/reparando", response_model=EquipoOut)
def marcar_reparando(equipo_id: int, db: Session = Depends(get_db)):
    return crud_equipos.update_equipo(
        db, equipo_id, EquipoUpdate(estado="en_reparacion")
    )


@router.patch("/{equipo_id}/listo", response_model=EquipoOut)
def marcar_listo(equipo_id: int, db: Session = Depends(get_db)):
    obj = crud_equipos.marcar_equipo_listo(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


@router.patch("/{equipo_id}/cancelar", response_model=EquipoOut)
def cancelar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = crud_equipos.cancelar_equipo(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# =====================================================
# 📣 NOTIFICACIONES
# =====================================================
@router.post("/{equipo_id}/notificar")
def notificar_equipo(
    equipo_id: int,
    payload: EquipoNotificar,
    db: Session = Depends(get_db),
):
    equipo = crud_equipos.get_equipo(db, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    if "email" in payload.via:
        if not equipo.cliente_correo:
            raise HTTPException(status_code=400, detail="No hay correo")

        enviar_email_reparacion(
            to_email=equipo.cliente_correo,
            cliente_nombre=equipo.cliente_nombre,
            ticket_id=str(equipo.id),
            modelo=equipo.modelo,
            falla=equipo.fallo,
            message_from_front=payload.message,
        )

    return {"ok": True, "equipo_id": equipo.id}


# =====================================================
# 🔍 OBTENER / ACTUALIZAR / ELIMINAR
# =====================================================
@router.get("/{equipo_id}", response_model=EquipoOut)
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = crud_equipos.get_equipo(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404)
    return obj


@router.patch("/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(
    equipo_id: int,
    payload: EquipoUpdate,
    db: Session = Depends(get_db),
):
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404)
    return obj


@router.delete("/{equipo_id}", status_code=204)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    if not crud_equipos.delete_equipo(db, equipo_id):
        raise HTTPException(status_code=404)
