# equipos_router.py
"""
Router completo para /equipos con:
- creación de equipos (genera QR y devuelve qr_url + qr_base64)
- listar, filtros y cambios de estado
- subir fotos al último equipo
- notificaciones por email
- endpoints para decodificar QR (archivo multipart y base64)
- endpoint GET /equipos/{id}/qr para servir la imagen PNG del QR

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
    Response,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Ajusta estas importaciones a la estructura de tu proyecto
from database import SessionLocal, engine, Base
from services.email_equipo import enviar_email_reparacion
from schemas.equipo import (
    EquipoCreate,
    EquipoUpdate,
    EquipoOut,
    EquipoNotificar,
)
from crud import equipos as crud_equipos

# crea tablas si no existen (ajusta si ya lo haces en otro lado)
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/equipos", tags=["Equipos"])

# =====================================================
# 📂 CARPETAS
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
# 🔧 Helpers para OpenCV
# =====================================================
_detector = cv2.QRCodeDetector()


def pil_to_cv2_bgr(pil_image: Image.Image) -> np.ndarray:
    """Convierte PIL Image -> OpenCV BGR numpy array"""
    rgb = np.array(pil_image.convert("RGB"))
    # PIL usa RGB, OpenCV suele usar BGR
    return rgb[:, :, ::-1].copy()


# =====================================================
# 🧩 UTIL: Intenta decodificar QR con transformaciones (OpenCV)
# =====================================================
def try_decode_qr(pil_image: Image.Image) -> Optional[str]:
    """
    Intenta decodificar QR usando varias transformaciones:
    - imagen original
    - grayscale
    - autocontrast
    - rotaciones 90/180/270
    Retorna el primer texto encontrado o None.
    """
    candidates: List[Image.Image] = []

    # versión base
    try:
        candidates.append(pil_image.convert("RGB"))
    except Exception:
        pass

    # grayscale + autocontrast
    try:
        g = ImageOps.grayscale(pil_image)
        candidates.append(g)
    except Exception:
        pass

    try:
        ac = ImageOps.autocontrast(pil_image)
        candidates.append(ac)
    except Exception:
        pass

    # rotaciones (aplicar a la imagen base y a autocontrast si existe)
    base_images = [candidates[0]] if candidates else []
    if len(candidates) > 1:
        base_images.extend([img for img in candidates[1:]])

    for base_img in base_images:
        for rot in (0, 90, 180, 270):
            try:
                if rot == 0:
                    img = base_img
                else:
                    img = base_img.rotate(rot, expand=True)
                candidates.append(img)
            except Exception:
                pass

    # ahora intentar decodificar cada candidato usando OpenCV
    for img in candidates:
        try:
            cv_img = pil_to_cv2_bgr(img)
            # detectAndDecode devuelve (data, points, straight_qrcode)
            data, points, _ = _detector.detectAndDecode(cv_img)
            if data and isinstance(data, str) and data.strip():
                return data.strip()
        except Exception:
            # ignorar y continuar con el siguiente intento
            continue

    return None


# =====================================================
# UTIL: genera QR en memoria y retorna (bytes_png, base64_str)
# =====================================================
def generar_qr_bytes_and_base64(text: str) -> (bytes, str):
    import qrcode

    qr = qrcode.make(str(text))
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    b = buffer.getvalue()
    b64 = base64.b64encode(b).decode("utf-8")
    return b, b64


# =====================================================
# 🚀 CREAR EQUIPO (genera QR con el ID) - DEVUELVE equipo + qr_url + qr_base64
# =====================================================
@router.post("/", status_code=status.HTTP_201_CREATED)
def crear_equipo(
    payload: EquipoCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Crea el equipo, genera QR (imagen PNG), guarda la URL en la BD y
    devuelve JSON con:
      {
        "equipo": { ... },         # representación serializada del equipo (EquipoOut)
        "qr_url": "https://.../static/qrs/equipos/xxxx.png",
        "qr_base64": "iVBORw0K..."
      }
    Esto facilita que Flutter muestre la vista previa inmediatamente.
    """
    equipo = crud_equipos.create_equipo(db, payload)
    if not equipo:
        raise HTTPException(status_code=400, detail="No se pudo crear el equipo")

    # Generar QR (conteniendo solo el ID)
    qr_bytes, qr_base64 = generar_qr_bytes_and_base64(str(equipo.id))

    # Guardar en disco
    qr_filename = f"{uuid.uuid4().hex}.png"
    qr_path = QR_DIR / qr_filename
    try:
        with open(qr_path, "wb") as fh:
            fh.write(qr_bytes)
    except Exception as e:
        # No es fatal: intentamos seguir y devolver base64 en la respuesta
        pass

    qr_url = absolute_url(request, f"/static/qrs/equipos/{qr_filename}")

    # Guardar la URL en el registro del equipo
    updated = crud_equipos.set_equipo_qr(db, equipo.id, qr_url)
    if not updated:
        # aún devolvemos la base64 para que frontend pueda mostrar algo
        response_equipo = EquipoOut.from_orm(equipo).dict()
        return {"equipo": response_equipo, "qr_url": qr_url, "qr_base64": qr_base64}

    # serializar equipo actualizado
    response_equipo = EquipoOut.from_orm(updated).dict()
    return {"equipo": response_equipo, "qr_url": qr_url, "qr_base64": qr_base64}


# =====================================================
# Endpoint para servir la imagen PNG del QR (por id)
# =====================================================
@router.get("/{equipo_id}/qr")
def get_qr_image(equipo_id: int):
    """
    Retorna image/png del primer archivo que encuentre en static/qrs/equipos
    que contenga el equipo_id en su contenido (si fue generado por este router)
    En nuestro caso generamos nombres UUID, así que busca en la BD la qr_url.
    """
    # Para evitar dependencias con request/DB dentro de este helper, abrimos sesión rápida
    db = SessionLocal()
    try:
        equipo = crud_equipos.get_equipo(db, equipo_id)
    finally:
        db.close()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Si no tiene qr_url, 404
    qr_url = getattr(equipo, "qr_url", None)
    if not qr_url:
        raise HTTPException(status_code=404, detail="QR no encontrado para este equipo")

    # qr_url es una URL absoluta tipo https://.../static/qrs/equipos/xxx.png
    # Convertimos a path relativo y servimos el archivo si existe
    try:
        filename = Path(qr_url).name
        file_path = QR_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo QR no encontrado en servidor")
        fh = open(file_path, "rb")
        return StreamingResponse(fh, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🔍 LISTAR EQUIPOS (SOLO ACTIVOS)
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
def equipos_en_reparacion(db: Session = Depends(get_db)):
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
    # Validación simple de tipo
    for f in (front, back):
        if not f.content_type or not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Ambos archivos deben ser imágenes")

    saved_paths: List[Path] = []

    try:
        # front
        ext_front = Path(front.filename).suffix.lower() or ".jpg"
        name_front = f"{uuid.uuid4().hex}{ext_front}"
        path_front = UPLOAD_DIR / name_front
        with open(path_front, "wb") as fh:
            fh.write(await front.read())
        url_front = absolute_url(request, f"/static/uploads/equipos/{name_front}")
        saved_paths.append(path_front)

        # back
        ext_back = Path(back.filename).suffix.lower() or ".jpg"
        name_back = f"{uuid.uuid4().hex}{ext_back}"
        path_back = UPLOAD_DIR / name_back
        with open(path_back, "wb") as fh:
            fh.write(await back.read())
        url_back = absolute_url(request, f"/static/uploads/equipos/{name_back}")
        saved_paths.append(path_back)

        ultimo = crud_equipos.get_last_equipo(db)
        if not ultimo:
            # limpiezas locales
            for p in saved_paths:
                p.unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="No hay equipos registrados")

        json_fotos = json.dumps({"front": url_front, "back": url_back})
        updated = crud_equipos.set_equipo_foto_json(db, ultimo.id, json_fotos)
        if not updated:
            raise HTTPException(status_code=500, detail="No se pudo guardar las fotos")
        return updated

    except HTTPException:
        raise
    except Exception as e:
        for p in saved_paths:
            p.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# 🔄 CAMBIOS DE ESTADO
# =====================================================
@router.patch("/{equipo_id}/reparando", response_model=EquipoOut)
def marcar_reparando(equipo_id: int, db: Session = Depends(get_db)):
    payload = EquipoUpdate(estado="en_reparacion")
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# 🔥 MARCAR LISTO (ARCHIVA POR DEFECTO)
@router.patch("/{equipo_id}/listo", response_model=EquipoOut)
def marcar_listo(equipo_id: int, db: Session = Depends(get_db)):
    """
    Marca el equipo como LISTO y lo ARCHIVA para que
    deje de aparecer en la lista principal
    """
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
# 📣 NOTIFICAR CLIENTE
# =====================================================
@router.post("/{equipo_id}/notificar", status_code=status.HTTP_200_OK)
def notificar_equipo(
    equipo_id: int,
    payload: EquipoNotificar,
    db: Session = Depends(get_db),
):
    equipo = crud_equipos.get_equipo(db, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    enviados = []

    if "email" in payload.via:
        if not equipo.cliente_correo:
            raise HTTPException(
                status_code=400,
                detail="El equipo no tiene correo registrado",
            )

        try:
            enviar_email_reparacion(
                to_email=equipo.cliente_correo,
                cliente_nombre=equipo.cliente_nombre,
                ticket_id=str(equipo.id),
                modelo=equipo.modelo,
                falla=equipo.fallo,
                message_from_front=payload.message,
            )
        except Exception as e:
            # registra el error y responde 500
            print("❌ ERROR enviando correo:", e)
            raise HTTPException(
                status_code=500,
                detail=f"Error enviando correo: {str(e)}"
            )

        enviados.append("email")

    return {
        "equipo_id": equipo.id,
        "estado": equipo.estado,
        "notificado_via": enviados,
        "message": payload.message,
    }


# =====================================================
# 🔍 OBTENER POR ID (INCLUYE ARCHIVADOS)
# =====================================================
@router.get("/{equipo_id}", response_model=EquipoOut)
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    obj = crud_equipos.get_equipo(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# =====================================================
# ✏️ ACTUALIZAR
# =====================================================
@router.patch("/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(
    equipo_id: int,
    payload: EquipoUpdate,
    db: Session = Depends(get_db),
):
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# =====================================================
# 🗑️ ELIMINAR (BORRADO LÓGICO)
# =====================================================
@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    ok = crud_equipos.delete_equipo(db, equipo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return None


# =====================================================
# 📷 LEER QR DESDE IMAGEN Y DEVOLVER EQUIPO (multipart/form-data)
# =====================================================
@router.post("/qr/decode", response_model=EquipoOut)
async def decode_qr_and_get_equipo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Recibe una imagen (multipart/form-data) con un QR.
    El QR debe contener únicamente el ID numérico del equipo.
    Devuelve el Equipo correspondiente (o 404 si no existe/no se detecta QR).
    """
    # Validaciones básicas
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Archivo no es una imagen")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 5MB)")

    try:
        # Abrir imagen con PIL de forma segura
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        qr_text = try_decode_qr(image)
        if not qr_text:
            raise HTTPException(status_code=404, detail="No se encontró QR en la imagen")

        # Validación: esperamos un ID numérico
        if not qr_text.isdigit():
            raise HTTPException(status_code=400, detail="El QR no contiene un ID de equipo válido")

        equipo_id = int(qr_text)
        equipo = crud_equipos.get_equipo(db, equipo_id)
        if not equipo:
            raise HTTPException(status_code=404, detail="Equipo no encontrado")

        return equipo

    except HTTPException:
        # re-lanzar HTTPException sin envolverla
        raise
    except Exception as e:
        # En desarrollo puedes retornar str(e). En producción usa mensaje genérico.
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# =====================================================
# 📷 LEER QR DESDE BASE64 (JSON)
# =====================================================
class ImageBase64Payload(BaseModel):
    image_base64: str  # data:image/png;base64,...


@router.post("/qr/decode_base64", response_model=EquipoOut)
def decode_qr_base64(payload: ImageBase64Payload, db: Session = Depends(get_db)):
    """
    Recibe JSON con image_base64 y devuelve el equipo.
    Útil para clientes web/móvil que envían la imagen como base64.
    """
    try:
        data = payload.image_base64
        # eliminar header si lo trae: data:image/png;base64,AAA...
        if "," in data:
            _, data = data.split(",", 1)
        file_bytes = base64.b64decode(data)
        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 5MB)")

        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")

        qr_text = try_decode_qr(image)
        if not qr_text:
            raise HTTPException(status_code=404, detail="No se encontró QR en la imagen")

        if not qr_text.isdigit():
            raise HTTPException(status_code=400, detail="El QR no contiene un ID de equipo válido")

        equipo_id = int(qr_text)
        equipo = crud_equipos.get_equipo(db, equipo_id)
        if not equipo:
            raise HTTPException(status_code=404, detail="Equipo no encontrado")
        return equipo

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
