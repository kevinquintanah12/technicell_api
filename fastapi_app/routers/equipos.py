from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.equipo import Equipo
from schemas.equipo import (
    EquipoCreate,
    EquipoUpdate,
    EquipoOut,
)
from crud import equipos as crud_equipos

router = APIRouter(
    prefix="/equipos",
    tags=["Equipos"],
)

# ======================================================
# CREAR EQUIPO
# ======================================================
@router.post("/", response_model=EquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(payload: EquipoCreate, db: Session = Depends(get_db)):
    return crud_equipos.create_equipo(db, payload)


# ======================================================
# LISTAR EQUIPOS ACTIVOS (NO ARCHIVADOS)
# ======================================================
@router.get("/", response_model=List[EquipoOut])
def listar_equipos(db: Session = Depends(get_db)):
    return crud_equipos.list_equipos_activos(db)


# ======================================================
# EQUIPOS PENDIENTES
# ======================================================
@router.get("/pendientes", response_model=List[EquipoOut])
def equipos_pendientes(db: Session = Depends(get_db)):
    return crud_equipos.list_equipos_por_estado(db, estado="pendiente")


# ======================================================
# EQUIPOS EN REPARACIÓN
# ======================================================
@router.get("/reparando", response_model=List[EquipoOut])
def equipos_reparando(db: Session = Depends(get_db)):
    return crud_equipos.list_equipos_por_estado(db, estado="reparando")


# ======================================================
# EQUIPOS LISTOS (INCLUYE ARCHIVADOS)
# ======================================================
@router.get("/reparados", response_model=List[EquipoOut])
def equipos_reparados(db: Session = Depends(get_db)):
    """
    Devuelve equipos con estado='listo' aunque estén archivados.
    """
    return crud_equipos.list_equipos_por_estado_incluyendo_archivados(
        db,
        estado="listo",
    )


# ======================================================
# MARCAR COMO REPARANDO
# ======================================================
@router.patch("/{equipo_id}/reparando", response_model=EquipoOut)
def marcar_reparando(equipo_id: int, db: Session = Depends(get_db)):
    payload = EquipoUpdate(estado="reparando")
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# ======================================================
# MARCAR COMO LISTO (NO ARCHIVA)
# ======================================================
@router.patch("/{equipo_id}/listo", response_model=EquipoOut)
def marcar_listo(equipo_id: int, db: Session = Depends(get_db)):
    """
    Marca el equipo como LISTO.
    ⚠️ NO se archiva aquí.
    """
    payload = EquipoUpdate(estado="listo")
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# ======================================================
# ENTREGAR EQUIPO (ARCHIVA)
# ======================================================
@router.patch("/{equipo_id}/entregar", response_model=EquipoOut)
def entregar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    """
    Marca como ENTREGADO y archiva el registro.
    """
    obj = crud_equipos.marcar_equipo_entregado(db, equipo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# ======================================================
# CANCELAR EQUIPO
# ======================================================
@router.patch("/{equipo_id}/cancelar", response_model=EquipoOut)
def cancelar_equipo(
    equipo_id: int,
    motivo: Optional[str] = None,
    db: Session = Depends(get_db),
):
    payload = EquipoUpdate(
        estado="cancelado",
        motivo_cancelacion=motivo,
    )
    obj = crud_equipos.update_equipo(db, equipo_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return obj


# ======================================================
# ELIMINAR (ARCHIVAR MANUAL)
# ======================================================
@router.delete("/{equipo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_equipo(equipo_id: int, db: Session = Depends(get_db)):
    ok = crud_equipos.archivar_equipo(db, equipo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return None
