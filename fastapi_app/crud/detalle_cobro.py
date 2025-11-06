from sqlalchemy.orm import Session
from models.detalle_cobro import DetalleCobro
from models.productos import Producto
from schemas.detalle_cobro import DetalleCobroCreate, DetalleCobroUpdate
from datetime import datetime

# --------------------------------------------
# Crear detalle de cobro
# --------------------------------------------
def create_detalle_cobro(db: Session, detalle: DetalleCobroCreate):
    producto = db.query(Producto).filter(Producto.id == detalle.producto_id).first()
    if not producto:
        return None  # Producto no encontrado

    subtotal = detalle.cantidad * producto.precio_venta

    db_detalle = DetalleCobro(
        cobro_id=detalle.cobro_id,
        producto_id=detalle.producto_id,
        producto_nombre=producto.nombre,  # ✅ Guardar nombre actual del producto
        cantidad=detalle.cantidad,
        precio_unitario=producto.precio_venta,  # ✅ Guardar precio actual
        subtotal=subtotal,
        fecha_registro=datetime.utcnow()
    )

    db.add(db_detalle)
    db.commit()
    db.refresh(db_detalle)
    return db_detalle


# --------------------------------------------
# Obtener todos los detalles
# --------------------------------------------
def get_detalles_cobro(db: Session, skip: int = 0, limit: int = 100):
    return db.query(DetalleCobro).offset(skip).limit(limit).all()


# --------------------------------------------
# Obtener detalle por ID
# --------------------------------------------
def get_detalle_cobro_by_id(db: Session, detalle_id: int):
    return db.query(DetalleCobro).filter(DetalleCobro.id == detalle_id).first()


# --------------------------------------------
# Actualizar detalle
# --------------------------------------------
def update_detalle_cobro(db: Session, detalle_id: int, detalle: DetalleCobroUpdate):
    db_detalle = db.query(DetalleCobro).filter(DetalleCobro.id == detalle_id).first()
    if not db_detalle:
        return None

    if detalle.cantidad is not None:
        db_detalle.cantidad = detalle.cantidad
        db_detalle.subtotal = db_detalle.cantidad * db_detalle.precio_unitario

    if detalle.precio_unitario is not None:
        db_detalle.precio_unitario = detalle.precio_unitario
        db_detalle.subtotal = db_detalle.cantidad * db_detalle.precio_unitario

    db.commit()
    db.refresh(db_detalle)
    return db_detalle


# --------------------------------------------
# Eliminar detalle
# --------------------------------------------
def delete_detalle_cobro(db: Session, detalle_id: int):
    db_detalle = db.query(DetalleCobro).filter(DetalleCobro.id == detalle_id).first()
    if not db_detalle:
        return None
    db.delete(db_detalle)
    db.commit()
    return True
