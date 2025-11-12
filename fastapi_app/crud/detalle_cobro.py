from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
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

    # Verificar stock disponible
    if producto.stock_actual < detalle.cantidad:
        raise Exception(f"Stock insuficiente para el producto '{producto.nombre}'")

    # Calcular subtotal
    subtotal = producto.precio_venta * detalle.cantidad

    # Crear el registro
    db_detalle = DetalleCobro(
        producto_id=detalle.producto_id,
        cantidad=detalle.cantidad,
        subtotal=subtotal
    )

    # Actualizar stock del producto
    producto.stock_actual -= detalle.cantidad

    db.add(db_detalle)
    db.commit()
    db.refresh(db_detalle)

    return {
        "id": db_detalle.id,
        "producto": producto.nombre,
        "precio_venta": producto.precio_venta,
        "cantidad": db_detalle.cantidad,
        "subtotal": db_detalle.subtotal,
        "stock_restante": producto.stock_actual
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

        # Verificar stock disponible
        if producto.stock_actual < detalle.cantidad:
            raise Exception(f"Stock insuficiente para el producto '{producto.nombre}'")

        # Calcular subtotal
        subtotal = producto.precio_venta * detalle.cantidad
        total_general += subtotal

        # Crear registro del detalle
        db_detalle = DetalleCobro(
            producto_id=detalle.producto_id,
            cantidad=detalle.cantidad,
            subtotal=subtotal
        )

        # Restar cantidad al stock del producto
        producto.stock_actual -= detalle.cantidad

        db.add(db_detalle)

        nuevos_detalles.append({
            "producto": producto.nombre,
            "precio_venta": producto.precio_venta,
            "cantidad": detalle.cantidad,
            "subtotal": subtotal,
            "stock_restante": producto.stock_actual
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


# --------------------------------------
# Obtener total vendido por producto
# --------------------------------------
def obtener_cantidades_vendidas_por_producto(db: Session):
    """
    Retorna una lista con cada producto, la cantidad total vendida y el monto total.
    """
    resultados = (
        db.query(
            Producto.id.label("producto_id"),
            Producto.nombre.label("producto"),
            func.sum(DetalleCobro.cantidad).label("cantidad_total_vendida"),
            func.sum(DetalleCobro.subtotal).label("monto_total")
        )
        .join(DetalleCobro, Producto.id == DetalleCobro.producto_id)
        .group_by(Producto.id, Producto.nombre)
        .all()
    )

    return [
        {
            "producto_id": r.producto_id,
            "producto": r.producto,
            "cantidad_total_vendida": int(r.cantidad_total_vendida or 0),
            "monto_total": float(r.monto_total or 0.0)
        }
        for r in resultados
    ]
