# equipos_router.py
"""
Router completo para /equipos con:
- creación de equipos (genera QR y devuelve qr_url + qr_base64)
- listar, filtros y cambios de estado
- subir fotos al último equipo
- notificaciones por email
- endpoints para decodificar QR (archivo multipart y base64)
- endpoint GET /equipos/{id}/qr para servir la imagen PNG del QR

Nuevos endpoints añadidos en esta versión:
- DELETE /equipos/{id}           -> borrado lógico (existente)
- DELETE /equipos/{id}/permanent -> borrado físico (archivos + BD)
- DELETE /equipos/clear          -> borrar todos (opcional permanent=true)
- GET    /equipos/search?q=...   -> buscar por letras (modelo/cliente/falla)
- PATCH  /equipos/{id}/reparado  -> marcar como reparado (fecha + estado)
- PATCH  /equipos/{id}/liquidar_anticipo -> registrar liquidación de anticipo
- PATCH  /equipos/{id}/archivar -> archivar (soft-delete) equipos reparados

Requiere que el módulo `crud.equipos` exponga (idealmente) funciones:
- get_equipo, list_equipos, create_equipo, update_equipo
- delete_equipo (lógico), permanent_delete_equipo (físico opcional)
- set_equipo_qr, set_equipo_foto_json, get_last_equipo
- marcar_equipo_listo  (opcional)

Si alguna función no existe, el router intenta usar "fallbacks" razonables.
"""
import uuid
import json
import io
import base64
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Tuple
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

    # rotaciones (aplicar a las imágenes base)
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
            data, points, _ = _detector.detectAndDecode(cv_img)
            if data and isinstance(data, str) and data.strip():
                return data.strip()
        except Exception:
            continue

    return None


# =====================================================
# UTIL: genera QR en memoria y retorna (bytes_png, base64_str)
# =====================================================
def generar_qr_bytes_and_base64(text: str) -> Tuple[bytes, str]:
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
    equipo = crud_equipos.create_equipo(db, payload)
    if not equipo:
        raise HTTPException(status_code=400, detail="No se pudo crear el equipo")

    qr_bytes, qr_base64 = generar_qr_bytes_and_base64(str(equipo.id))

    qr_filename = f"{uuid.uuid4().hex}.png"
    qr_path = QR_DIR / qr_filename
    try:
        with open(qr_path, "wb") as fh:
            fh.write(qr_bytes)
    except Exception:
        pass

    qr_url = absolute_url(request, f"/static/qrs/equipos/{qr_filename}")

    updated = crud_equipos.set_equipo_qr(db, equipo.id, qr_url)
    if not updated:
        response_equipo = EquipoOut.from_orm(equipo).dict()
        return {"equipo": response_equipo, "qr_url": qr_url, "qr_base64": qr_base64}

    response_equipo = EquipoOut.from_orm(updated).dict()
    return {"equipo": response_equipo, "qr_url": qr_url, "qr_base64": qr_base64}


# =====================================================
# Endpoint para servir la imagen PNG del QR (por id)
# =====================================================
@router.get("/{equipo_id}/qr")
def get_qr_image(equipo_id: int):
    db = SessionLocal()
    try:
        equipo = crud_equipos.get_equipo(db, equipo_id)
    finally:
        db.close()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    qr_url = getattr(equipo, "qr_url", None)
    if not qr_url:
        raise HTTPException(status_code=404, detail="QR no encontrado para este equipo")

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
# 🔍 LISTAR EQUIPOS (con opción de incluir archivados)
# =====================================================
@router.get("/", response_model=List[EquipoOut])
def listar_equipos(
    nombre_cliente: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    include_archived: Optional[bool] = Query(False),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    if nombre_cliente:
        return crud_equipos.get_equipos_by_cliente_nombre(db, nombre_cliente)

    try:
        return crud_equipos.list_equipos(
            db=db,
            skip=skip,
            limit=limit,
            cliente_nombre=nombre_cliente,
            estado=estado,
            include_archived=include_archived,
        )
    except TypeError:
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


@router.get("/reparados", response_model=List[EquipoOut])
def equipos_reparados(db: Session = Depends(get_db)):
    try:
        return crud_equipos.list_equipos(db, estado="listo", include_archived=True)
    except TypeError:
        return crud_equipos.list_equipos(db, estado="listo")


@router.get("/resumen_reparaciones", response_model=Dict[str, List[EquipoOut]])
def resumen_reparaciones(db: Session = Depends(get_db)):
    en_reparacion = crud_equipos.list_equipos(db, estado="en_reparacion")
    try:
        reparados = crud_equipos.list_equipos(db, estado="listo", include_archived=True)
    except TypeError:
        reparados = crud_equipos.list_equipos(db, estado="listo")
    return {"en_reparacion": en_reparacion, "reparados": reparados}


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
            raise HTTPException(status_code=400, detail="Ambos archivos deben ser imágenes")

    saved_paths: List[Path] = []

    try:
        ext_front = Path(front.filename).suffix.lower() or ".jpg"
        name_front = f"{uuid.uuid4().hex}{ext_front}"
        path_front = UPLOAD_DIR / name_front
        with open(path_front, "wb") as fh:
            fh.write(await front.read())
        url_front = absolute_url(request, f"/static/uploads/equipos/{name_front}")
        saved_paths.append(path_front)

        ext_back = Path(back.filename).suffix.lower() or ".jpg"
        name_back = f"{uuid.uuid4().hex}{ext_back}"
        path_back = UPLOAD_DIR / name_back
        with open(path_back, "wb") as fh:
            fh.write(await back.read())
        url_back = absolute_url(request, f"/static/uploads/equipos/{name_back}")
        saved_paths.append(path_back)

        ultimo = crud_equipos.get_last_equipo(db)
        if not ultimo:
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
# 🔄 CAMBIOS DE ESTADO (existentes)
# =====================================================
@router.patch("/{equipo_id}/reparando", response_model=EquipoOut)
def marcar_reparando(equipo_id: int, db: Session = Depends(get_db)):
    payload = EquipoUpdate(estado="en_reparacion")
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


@router.patch("/{equipo_id}/listo", response_model=EquipoOut)
def marcar_listo(equipo_id: int, db: Session = Depends(get_db)):
    try:
        obj = crud_equipos.marcar_equipo_listo(db, equipo_id)
    except AttributeError:
        payload = EquipoUpdate(estado="listo")
        obj = crud_equipos.update_equipo(db, equipo_id, payload)
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
#  NUEVOS ENDPOINTS SOLICITADOS
# =====================================================

# Modelo para liquidar anticipo
class AnticipoPayload(BaseModel):
    monto: Optional[float] = None
    notas: Optional[str] = None


@router.patch("/{equipo_id}/liquidar_anticipo", response_model=EquipoOut)
def liquidar_anticipo(equipo_id: int, payload: AnticipoPayload, db: Session = Depends(get_db)):
    """
    Marca el anticipo como liquidado. Guarda fecha y monto si se provee.
    """
    equipo = crud_equipos.get_equipo(db, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # intentamos usar un método específico del crud si existe
    try:
        obj = crud_equipos.liquidar_anticipo(db, equipo_id, monto=payload.monto, notas=payload.notas)
    except AttributeError:
        # Fallback: actualizamos columnas genéricas si existen
        update_payload = {}
        update_payload["anticipo_liquidado"] = True
        update_payload["anticipo_fecha_liquidacion"] = datetime.utcnow()
        if payload.monto is not None:
            update_payload["anticipo_monto"] = payload.monto
        if payload.notas:
            update_payload["anticipo_notas"] = payload.notas
        # convertimos a EquipoUpdate si posible
        try:
            eu = EquipoUpdate(**update_payload)
            obj = crud_equipos.update_equipo(db, equipo_id, eu)
        except Exception:
            # último recurso: levantamos error sobre esquema
            raise HTTPException(status_code=500, detail="No se pudo liquidar el anticipo con la configuración actual del CRUD")

    if not obj:
        raise HTTPException(status_code=500, detail="No se pudo guardar la liquidación del anticipo")
    return obj


@router.patch("/{equipo_id}/reparado", response_model=EquipoOut)
def marcar_reparado(equipo_id: int, db: Session = Depends(get_db)):
    """
    Marca el equipo como reparado (estado + fecha_reparacion).
    """
    equipo = crud_equipos.get_equipo(db, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    payload = None
    try:
        payload = EquipoUpdate(estado="reparado", fecha_reparacion=datetime.utcnow())
        obj = crud_equipos.update_equipo(db, equipo_id, payload)
    except Exception:
        # fallback simple
        payload = EquipoUpdate(estado="reparado")
        obj = crud_equipos.update_equipo(db, equipo_id, payload)

    if not obj:
        raise HTTPException(status_code=500, detail="No se pudo marcar como reparado")
    return obj


@router.patch("/{equipo_id}/archivar", response_model=EquipoOut)
def archivar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    """
    Archiva (soft-delete) un equipo. Ideal para "borrar" reparados sin eliminarlos físicamente.
    """
    equipo = crud_equipos.get_equipo(db, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # sólo permitimos archivar si está reparado/listo (según tu lógica)
    estado = getattr(equipo, "estado", None)
    if estado not in ("listo", "reparado", "finalizado", None):
        # permitimos archivar sólo si está reparado/listo
        raise HTTPException(status_code=400, detail="Sólo se pueden archivar equipos ya reparados/listos")

    try:
        obj = crud_equipos.archive_equipo(db, equipo_id)
    except AttributeError:
        # Fallback: marcamos una columna 'archivado' si existe
        try:
            eu = EquipoUpdate(archivado=True)
            obj = crud_equipos.update_equipo(db, equipo_id, eu)
        except Exception:
            raise HTTPException(status_code=500, detail="No se pudo archivar el equipo (falta soporte en CRUD)")

    if not obj:
        raise HTTPException(status_code=500, detail="No se pudo archivar el equipo")
    return obj


@router.get("/search", response_model=List[EquipoOut])
def search_equipos(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """
    Busca equipos por texto en campos como: modelo, cliente_nombre, fallo.
    Si el CRUD no implementa search_equipos, hacemos un filtro simple en memoria
    sobre list_equipos(limit=1000) (no óptimo pero funcional).
    """
    try:
        return crud_equipos.search_equipos(db, q)
    except AttributeError:
        # fallback: traer hasta 2000 y filtrar en Python
        try:
            items = crud_equipos.list_equipos(db, skip=0, limit=2000)
        except TypeError:
            items = crud_equipos.list_equipos(db)

        def matches(e):
            s = q.lower()
            for attr in ("modelo", "cliente_nombre", "fallo", "marca", "serie"):
                val = getattr(e, attr, None)
                if val and s in str(val).lower():
                    return True
            return False

        return [i for i in items if matches(i)]


# =====================================================
# 🗑️ ELIMINAR (BORRADO LÓGICO EXISTENTE)
# =====================================================
@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    ok = crud_equipos.delete_equipo(db, equipo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return None


@router.delete("/{equipo_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_equipo_permanente(equipo_id: int, db: Session = Depends(get_db)):
    """
    Borra físicamente el equipo y sus archivos (QR + fotos) si existe.
    Requiere que el CRUD exponga `permanent_delete_equipo(db, id)` o similar.
    """
    equipo = crud_equipos.get_equipo(db, equipo_id)
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # eliminar archivos asociados (fotos + qr)
    fotos_json = getattr(equipo, "fotos_json", None) or getattr(equipo, "fotos", None)
    if fotos_json:
        try:
            if isinstance(fotos_json, str):
                fj = json.loads(fotos_json)
            else:
                fj = fotos_json
            for v in fj.values():
                try:
                    fname = Path(v).name
                    p = UPLOAD_DIR / fname
                    if p.exists():
                        p.unlink(missing_ok=True)
                except Exception:
                    pass
        except Exception:
            pass

    qr_url = getattr(equipo, "qr_url", None)
    if qr_url:
        try:
            fname = Path(qr_url).name
            p = QR_DIR / fname
            if p.exists():
                p.unlink(missing_ok=True)
        except Exception:
            pass

    # intenta usar función del crud para borrado permanente
    try:
        ok = crud_equipos.permanent_delete_equipo(db, equipo_id)
        if not ok:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el equipo permanentemente")
    except AttributeError:
        # Fallback: llamamos a delete_equipo y luego intentamos remover de la tabla con SQL directo
        ok = crud_equipos.delete_equipo(db, equipo_id)
        if not ok:
            raise HTTPException(status_code=500, detail="No se pudo eliminar el equipo (fallback)")
        # Si necesitas borrado físico en BD, implementa permanent_delete_equipo en crud

    return None


@router.delete("/clear", status_code=status.HTTP_200_OK)
def clear_equipos(permanent: bool = Query(False), db: Session = Depends(get_db)):
    """
    Borra todos los equipos. Por defecto es "soft delete" (lógico). Si `permanent=true` intenta
    borrar físicamente registros y archivos (PELIGRO: irreversible).
    """
    items = crud_equipos.list_equipos(db, skip=0, limit=10000)
    deleted = []
    failed = []
    for e in items:
        try:
            if permanent:
                try:
                    res = crud_equipos.permanent_delete_equipo(db, e.id)
                except AttributeError:
                    # fallback: delete_equipo
                    res = crud_equipos.delete_equipo(db, e.id)
            else:
                res = crud_equipos.delete_equipo(db, e.id)
            if res:
                deleted.append(e.id)
            else:
                failed.append(e.id)
        except Exception:
            failed.append(e.id)

    return {"deleted": deleted, "failed": failed}


# =====================================================
# 📷 LEER QR DESDE IMAGEN Y DEVOLVER EQUIPO (multipart/form-data)
# =====================================================
@router.post("/qr/decode", response_model=EquipoOut)
async def decode_qr_and_get_equipo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Archivo no es una imagen")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máx 5MB)")

    try:
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
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# =====================================================
# 📷 LEER QR DESDE BASE64 (JSON)
# =====================================================
class ImageBase64Payload(BaseModel):
    image_base64: str  # data:image/png;base64,...


@router.post("/qr/decode_base64", response_model=EquipoOut)
def decode_qr_base64(payload: ImageBase64Payload, db: Session = Depends(get_db)):
    try:
        data = payload.image_base64
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
