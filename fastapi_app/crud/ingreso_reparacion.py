from sqlalchemy.orm import Session
from models.ingreso_reparacion import IngresoReparacion
from schemas.ingreso_reparacion import IngresoReparacionCreate, IngresoReparacionUpdate


def crear_ingreso(db: Session, data: IngresoReparacionCreate):
    nuevo = IngresoReparacion(**data.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def actualizar_ingreso(db: Session, ingreso_id: int, data: IngresoReparacionUpdate):
    ingreso = db.query(IngresoReparacion).filter(IngresoReparacion.id == ingreso_id).first()
    if not ingreso:
        return None

    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(ingreso, campo, valor)

    db.commit()
    db.refresh(ingreso)
    return ingreso
