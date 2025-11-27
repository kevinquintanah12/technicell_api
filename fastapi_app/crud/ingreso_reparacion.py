from sqlalchemy.orm import Session
from models.ingreso_reparacion import IngresoReparacion

def crear_ingreso(db: Session, data: dict):
    permitido = {
        "cliente_id",
        "cliente_nombre",
        "telefono",
        "equipo",
        "marca",
        "modelo",
        "falla",
        "observaciones",
        "foto1",
        "foto2",
        "foto3",
        "entregado",
        "fecha_ingreso",
    }

    data_filtrado = {k: v for k, v in data.items() if k in permitido}

    nuevo = IngresoReparacion(**data_filtrado)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo
