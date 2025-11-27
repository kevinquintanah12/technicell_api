from sqlalchemy.orm import Session
from models.ingreso_reparacion import IngresoReparacion


def crear_ingreso(db: Session, data: dict):
    nuevo = IngresoReparacion(**data)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def obtener_ingreso(db: Session, ingreso_id: int):
    return db.query(IngresoReparacion).filter(IngresoReparacion.id == ingreso_id).first()


def actualizar_ingreso(db: Session, ingreso_id: int, data: dict):
    ingreso = obtener_ingreso(db, ingreso_id)
    if not ingreso:
        return None

    for campo, valor in data.items():
        setattr(ingreso, campo, valor)

    db.commit()
    db.refresh(ingreso)
    return ingreso
