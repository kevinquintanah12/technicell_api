from sqlalchemy.orm import Session
from models.productos import Producto
from models.detalle_cobro import DetalleCobro
from schemas.productos import ProductoCreate, ProductoUpdate

# -----------------------------------------------------
# CRUD base
# -----------------------------------------------------

def get_producto(db: Session, producto_id: int):
    return db.query(Producto).filter(Producto.id == producto_id).first()


def get_productos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Producto).offset(skip).limit(limit).all()


def create_producto(db: Session, producto: ProductoCreate):
    db_producto = Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


def update_producto(db: Session, producto_id: int, producto: ProductoUpdate):
    db_producto = get_producto(db, producto_id)
    if not db_producto:
        return None

    for key, value in producto.dict(exclude_unset=True).items():
        setattr(db_producto, key, value)

    db.commit()
    db.refresh(db_producto)
    return db_producto


def delete_producto(db: Session, producto_id: int):
    db_producto = get_producto(db, producto_id)
    if not db_producto:
        return None
    db.delete(db_producto)
    db.commit()
    return db_producto


# -----------------------------------------------------
# 🚀 Nueva función: registrar venta y actualizar stock
# -----------------------------------------------------

def registrar_venta(db: Session, producto_id: int, cantidad_vendida: int):
    """
    Resta del stock del producto la cantidad vendida.
    Retorna el producto actualizado o lanza un ValueError si no hay suficiente stock.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()

    if not producto:
        raise ValueError("Producto no encontrado.")

    if producto.stock_actual < cantidad_vendida:
        raise ValueError(f"Stock insuficiente. Solo hay {producto.stock_actual} unidades disponibles.")

    # 🔻 Restar stock
    producto.stock_actual -= cantidad_vendida

    # ⚠️ Verificar si queda por debajo del mínimo
    alerta = None
    if producto.stock_actual <= producto.stock_minimo:
        alerta = f"⚠️ Advertencia: El stock de '{producto.nombre}' está por debajo del mínimo ({producto.stock_actual} unidades)."

    db.commit()
    db.refresh(producto)

    return {
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "stock_restante": producto.stock_actual,
        "alerta": alerta
    }
