import uuid
import json
from pathlib import Path
from typing import List, Optional

import qrcode
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
from sqlalchemy.orm import Session

from database import SessionLocal, engine, Base
from schemas.equipo import (
    EquipoCreate,
    EquipoUpdate,
    EquipoOut,
    EquipoNotificar,
)
from crud import equipos as crud_equipos

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
# 🚀 CREAR EQUIPO
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

    qr_filename = f"{uuid.uuid4().hex}.png"
    qr_path = QR_DIR / qr_filename
    qrcode.make(str(equipo.id)).save(qr_path)

    qr_url = absolute_url(request, f"/static/qrs/equipos/{qr_filename}")
    return crud_equipos.set_equipo_qr(db, equipo.id, qr_url)


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
    for f in (front, back):
        if not f.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Ambos archivos deben ser imágenes")

    saved = []

    try:
        ext_front = Path(front.filename).suffix.lower()
        name_front = f"{uuid.uuid4().hex}{ext_front}"
        path_front = UPLOAD_DIR / name_front
        with open(path_front, "wb") as f:
            f.write(await front.read())
        url_front = absolute_url(request, f"/static/uploads/equipos/{name_front}")
        saved.append(path_front)

        ext_back = Path(back.filename).suffix.lower()
        name_back = f"{uuid.uuid4().hex}{ext_back}"
        path_back = UPLOAD_DIR / name_back
        with open(path_back, "wb") as f:
            f.write(await back.read())
        url_back = absolute_url(request, f"/static/uploads/equipos/{name_back}")
        saved.append(path_back)

        ultimo = crud_equipos.get_last_equipo(db)
        if not ultimo:
            raise HTTPException(status_code=404, detail="No hay equipos registrados")

        json_fotos = json.dumps({"front": url_front, "back": url_back})
        return crud_equipos.set_equipo_foto_json(db, ultimo.id, json_fotos)

    except Exception as e:
        for p in saved:
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


# 🔥 ESTE ES EL IMPORTANTE 🔥
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

        enviar_email(
            destinatario=equipo.cliente_correo,
            asunto="Estado de tu equipo",
            mensaje=payload.message,
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
