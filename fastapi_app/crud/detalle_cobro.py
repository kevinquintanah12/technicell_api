from typing import List
from sqlalchemy.orm import Session
from models.detalle_cobro import DetalleCobro
from models.productos import Producto
from schemas.detalle_cobro import DetalleCobroCreate

# --------------------------------------
# Crear un solo detalle de cobro
# --------------------------------------
def crear_detalle_cobro(db: Session, detalle: DetalleCobroCreate):
    # Buscar el producto
    producto = db.query(Producto).filter(Producto.id == detalle.producto_id).first()

    if not producto:
        raise Exception("Producto no encontrado")

    # Calcular subtotal
    subtotal = producto.precio_venta * detalle.cantidad

    # Crear el registro
    db_detalle = DetalleCobro(
        producto_id=detalle.producto_id,
        cantidad=detalle.cantidad,
        subtotal=subtotal
    )

    db.add(db_detalle)
    db.commit()
    db.refresh(db_detalle)

    return {
        "id": db_detalle.id,
        "producto": producto.nombre,
        "precio_venta": producto.precio_venta,
        "cantidad": db_detalle.cantidad,
        "subtotal": db_detalle.subtotal
    }


# --------------------------------------
# Crear varios detalles de cobro a la vez
# --------------------------------------
def crear_detalles_cobro(db: Session, detalles: List[DetalleCobroCreate]):
    nuevos_detalles = []
    total_general = 0

    for detalle in detalles:
        # Buscar producto
        producto = db.query(Producto).filter(Producto.id == detalle.producto_id).first()

        if not producto:
            raise Exception(f"Producto con ID {detalle.producto_id} no encontrado")

        # Calcular subtotal
        subtotal = producto.precio_venta * detalle.cantidad
        total_general += subtotal

        # Crear registro del detalle
        db_detalle = DetalleCobro(
            producto_id=detalle.producto_id,
            cantidad=detalle.cantidad,
            subtotal=subtotal
        )

        db.add(db_detalle)

        nuevos_detalles.append({
            "producto": producto.nombre,
            "precio_venta": producto.precio_venta,
            "cantidad": detalle.cantidad,
            "subtotal": subtotal
        })

    db.commit()

    return {
        "detalles": nuevos_detalles,
        "total_general": total_general
    }


# --------------------------------------
# Obtener todos los detalles de cobro
# --------------------------------------
def obtener_detalles_cobro(db: Session):
    detalles = db.query(DetalleCobro).all()
    resultado = []
    for d in detalles:
        producto = db.query(Producto).filter(Producto.id == d.producto_id).first()
        resultado.append({
            "id": d.id,
            "producto": producto.nombre if producto else "Desconocido",
            "precio_venta": producto.precio_venta if producto else 0,
            "cantidad": d.cantidad,
            "subtotal": d.subtotal
        })
    return resultado
