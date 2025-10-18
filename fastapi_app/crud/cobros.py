from sqlalchemy.orm import Session
from models.cobros import Cobro
from schemas.cobros import CobroCreate, CobroUpdate

def create_cobro(db: Session, cobro: CobroCreate):
    if cobro.anticipo > cobro.monto_total:
        raise ValueError("El anticipo no puede ser mayor al monto total")
    saldo = float(cobro.monto_total) - float(cobro.anticipo)
    db_cobro = Cobro(
        cliente_id=cobro.cliente_id,
        equipo_id=cobro.equipo_id,
        monto_total=cobro.monto_total,
        anticipo=cobro.anticipo,
        saldo_pendiente=saldo,
        metodo_pago=cobro.metodo_pago
    )
    db.add(db_cobro)
    db.commit()
    db.refresh(db_cobro)
    return db_cobro

def get_cobros(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Cobro).offset(skip).limit(limit).all()

def update_cobro(db: Session, cobro_id: int, cobro_update: CobroUpdate):
    cobro = db.query(Cobro).filter(Cobro.id == cobro_id).first()
    if not cobro:
        return None
    for key, value in cobro_update.dict(exclude_unset=True).items():
        setattr(cobro, key, value)
    # recalcular saldo pendiente si anticipo cambia
    if cobro_update.anticipo is not None:
        cobro.saldo_pendiente = cobro.monto_total - cobro.anticipo
    db.commit()
    db.refresh(cobro)
    return cobro
