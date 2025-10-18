from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from database import get_db
from crud import cobros as crud_cobros
from schemas.cobros import CobroCreate, CobroUpdate, CobroOut
from utils.tickets import generar_ticket_profesional

router = APIRouter(prefix="/cobros", tags=["Cobros"])

# -----------------------------
# Crear cobro y generar ticket
# -----------------------------
@router.post("/", response_model=CobroOut)
def crear_cobro(cobro: CobroCreate, db: Session = Depends(get_db)):
    try:
        nuevo_cobro = crud_cobros.create_cobro(db, cobro)
        # Generar ticket considerando anticipo y restante
        archivo_ticket = generar_ticket_profesional(
            nuevo_cobro,
            incluir_restante=True  # ✅ Puedes usar un flag para mostrar saldo pendiente
        )
        return {**nuevo_cobro.__dict__, "ticket": archivo_ticket}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------
# Listar cobros
# -----------------------------
@router.get("/", response_model=list[CobroOut])
def listar_cobros(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud_cobros.get_cobros(db, skip, limit)

# -----------------------------
# Actualizar cobro y regenerar ticket
# -----------------------------
@router.put("/{cobro_id}", response_model=CobroOut)
def actualizar_cobro(cobro_id: int, cobro: CobroUpdate, db: Session = Depends(get_db)):
    updated = crud_cobros.update_cobro(db, cobro_id, cobro)
    if not updated:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    
    # Regenerar ticket actualizado con anticipo/restante
    archivo_ticket = generar_ticket_profesional(updated, incluir_restante=True)
    return {**updated.__dict__, "ticket": archivo_ticket}

# -----------------------------
# Descargar ticket PDF
# -----------------------------
@router.get("/ticket/{cobro_id}")
def descargar_ticket(cobro_id: int, db: Session = Depends(get_db)):
    cobro = db.query(crud_cobros.Cobro).filter(crud_cobros.Cobro.id == cobro_id).first()
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    
    archivo_ticket = generar_ticket_profesional(cobro, incluir_restante=True)
    return FileResponse(
        archivo_ticket,
        media_type="application/pdf",
        filename=f"ticket_{cobro.id}.pdf"
    )
