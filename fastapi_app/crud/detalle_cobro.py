# crud/detalle_cobro.py
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.detalle_cobro import DetalleCobro
from models.productos import Producto


# --------------------------------------
# Crear varios detalles de cobro (CORREGIDO)
# --------------------------------------
def crear_detalles_cobro(db: Session, detalles: List[Dict[str, Any]]):
    nuevos_detalles = []
    total_general = 0

    for detalle in detalles:

        # ✔ Obtener datos desde dict
        producto_id = detalle.get("producto_id")
        cantidad = detalle.get("cantidad")

        if not producto_id or not cantidad:
            raise Exception("Cada detalle debe incluir producto_id y cantidad")

        # Buscar producto
        producto = db.query(Producto).filter(Producto.id == producto_id).first()

        if not producto:
            raise Exception(f"Producto con ID {producto_id} no encontrado")

        # Verificar stock disponible
        if producto.stock_actual < cantidad:
            raise Exception(f"Stock insuficiente para el producto '{producto.nombre}'")

        # Calcular subtotal
        subtotal = producto.precio_venta * cantidad
        total_general += subtotal

        # Crear registro del detalle
        db_detalle = DetalleCobro(
            producto_id=producto_id,
            cantidad=cantidad,
            subtotal=subtotal
        )

        # Actualizar stock
        producto.stock_actual -= cantidad

        db.add(db_detalle)

        nuevos_detalles.append({
            "producto": producto.nombre,
            "precio_venta": producto.precio_venta,
            "cantidad": cantidad,
            "subtotal": subtotal,
            "stock_restante": producto.stock_actual
        })

    db.commit()

    return {
        "detalles": nuevos_detalles,
        "total_general": total_general
    }
