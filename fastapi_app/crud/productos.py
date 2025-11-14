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

    # -------- VALIDACIONES --------
    if producto.stock_actual < 0:
        raise ValueError("El stock actual no puede ser negativo.")

    if producto.stock_minimo < 0:
        raise ValueError("El stock mínimo no puede ser negativo.")

    if producto.stock_minimo > producto.stock_actual:
        raise ValueError("El stock mínimo no puede ser mayor que el stock actual.")

    db_producto = Producto(**producto.dict())
    db.add(db_producto)
    db.commit()
    db.refresh(db_producto)
    return db_producto


def update_producto(db: Session, producto_id: int, producto: ProductoUpdate):
    db_producto = get_producto(db, producto_id)
    if not db_producto:
        return None

    data = producto.dict(exclude_unset=True)

    # Valores que se actualizarían
    nuevo_stock_actual = data.get("stock_actual", db_producto.stock_actual)
    nuevo_stock_minimo = data.get("stock_minimo", db_producto.stock_minimo)

    # -------- VALIDACIONES --------
    if nuevo_stock_actual < 0:
        raise ValueError("El stock actual no puede ser negativo.")

    if nuevo_stock_minimo < 0:
        raise ValueError("El stock mínimo no puede ser negativo.")

    if nuevo_stock_minimo > nuevo_stock_actual:
        raise ValueError("El stock mínimo no puede ser mayor que el stock actual.")

    # Aplicar cambios
    for key, value in data.items():
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
    return True  # 🔹 mejor para el router


# -----------------------------------------------------
# 🚀 Nueva función: registrar venta y actualizar stock
# -----------------------------------------------------

def registrar_venta(db: Session, producto_id: int, cantidad_vendida: int):
    """
    Resta del stock del producto la cantidad vendida.
    Retorna el producto actualizado o lanza un ValueError si no hay suficiente stock.
    """

    # Validar cantidad
    if cantidad_vendida <= 0:
        raise ValueError("La cantidad vendida debe ser mayor a 0.")

    producto = db.query(Producto).filter(Producto.id == producto_id).first()

    if not producto:
        raise ValueError("Producto no encontrado.")

    if producto.stock_actual < cantidad_vendida:
        raise ValueError(
            f"Stock insuficiente. Solo hay {producto.stock_actual} unidades disponibles."
        )

    # 🔻 Restar stock
    producto.stock_actual -= cantidad_vendida

    # ⚠️ Verificar si queda por debajo del mínimo
    alerta = None
    if producto.stock_actual <= producto.stock_minimo:
        alerta = (
            f"⚠️ Advertencia: El stock de '{producto.nombre}' está "
            f"por debajo del mínimo ({producto.stock_actual} unidades)."
        )

    db.commit()
    db.refresh(producto)

    return {
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "stock_restante": producto.stock_actual,
        "alerta": alerta
    }
