from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.order import Order, Payment
from app.schemas.orders import OrderCreate, OrderUpdate, PaymentCreate


def get_orders(
    db: Session,
    weaver_user_id: int,
    *,
    status_filter: str | None = None,
    category_id: int | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Order], int]:
    """Return paginated orders for a weaver, with optional filters."""
    query = (
        db.query(Order)
        .filter(Order.weaver_user_id == weaver_user_id, Order.is_deleted.is_(False))
        .options(joinedload(Order.category), joinedload(Order.buyer), joinedload(Order.payments))
    )
    if status_filter:
        query = query.filter(Order.status == status_filter)
    if category_id:
        query = query.filter(Order.category_id == category_id)

    total = query.count()
    orders = (
        query.order_by(Order.order_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return orders, total


def get_order_by_id(db: Session, order_id: int) -> Order | None:
    return (
        db.query(Order)
        .filter(Order.id == order_id, Order.is_deleted.is_(False))
        .options(joinedload(Order.category), joinedload(Order.buyer), joinedload(Order.payments))
        .first()
    )


def deduct_inventory_for_order(db: Session, user_id: int, category_name: str, quantity: int):
    from app.models.inventory import Inventory
    from app.services.planner import MATERIAL_FACTORS
    
    silk_f, cotton_f, dye_f = MATERIAL_FACTORS.get(category_name, (0.0, 0.0, 0.0))
    if silk_f == 0.0 and cotton_f == 0.0 and dye_f == 0.0:
        return
        
    items = db.query(Inventory).filter(Inventory.user_id == user_id).all()
    if not items:
        from app.routers.inventory import ensure_default_inventory
        items = ensure_default_inventory(db, user_id)
        
    for item in items:
        name = item.material_name.lower()
        if "silk" in name:
            item.current_stock = max(0.0, round(item.current_stock - quantity * silk_f, 2))
        elif "cotton" in name:
            item.current_stock = max(0.0, round(item.current_stock - quantity * cotton_f, 2))
        elif "dye" in name or "chemical" in name:
            item.current_stock = max(0.0, round(item.current_stock - quantity * dye_f, 2))
            
    db.commit()


def restore_inventory_for_order(db: Session, user_id: int, category_name: str, quantity: int):
    from app.models.inventory import Inventory
    from app.services.planner import MATERIAL_FACTORS
    
    silk_f, cotton_f, dye_f = MATERIAL_FACTORS.get(category_name, (0.0, 0.0, 0.0))
    if silk_f == 0.0 and cotton_f == 0.0 and dye_f == 0.0:
        return
        
    items = db.query(Inventory).filter(Inventory.user_id == user_id).all()
    for item in items:
        name = item.material_name.lower()
        if "silk" in name:
            item.current_stock = round(item.current_stock + quantity * silk_f, 2)
        elif "cotton" in name:
            item.current_stock = round(item.current_stock + quantity * cotton_f, 2)
        elif "dye" in name or "chemical" in name:
            item.current_stock = round(item.current_stock + quantity * dye_f, 2)
            
    db.commit()


def create_order(db: Session, weaver_user_id: int, data: OrderCreate) -> Order:
    # Get product category name to apply conversion rules
    from app.models.order import ProductCategory
    cat = db.query(ProductCategory).filter(ProductCategory.id == data.category_id).first()
    cat_name = cat.name if cat else "Silk Saree"

    # Calculate net profit
    if data.category_id == 5:
        p_cost = 3500.0
    elif data.category_id == 1:
        p_cost = 1200.0
    else:
        p_cost = data.price_per_unit * 0.65
        
    prod_cost_total = data.quantity * p_cost
    overhead = 0.1 * prod_cost_total
    net_prof = (data.quantity * data.price_per_unit) - (prod_cost_total + overhead)

    order = Order(
        weaver_user_id=weaver_user_id,
        category_id=data.category_id,
        buyer_id=data.buyer_id,
        quantity=data.quantity,
        price_per_unit=data.price_per_unit,
        total_value=data.quantity * data.price_per_unit,
        net_profit=net_prof,
        order_date=data.order_date,
        expected_delivery_date=data.expected_delivery_date,
        expected_payment_date=data.expected_payment_date,
        advance_amount=data.advance_amount,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Deduct stock items dynamically
    try:
        deduct_inventory_for_order(db, weaver_user_id, cat_name, data.quantity)
    except Exception as e:
        print(f"Failed to deduct stock for order: {e}")

    return order


def update_order(db: Session, order: Order, data: OrderUpdate) -> Order:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    # Recalculate total if quantity or price changed
    if "quantity" in update_data or "price_per_unit" in update_data:
        order.total_value = order.quantity * order.price_per_unit
        if order.category_id == 5:
            p_cost = 3500.0
        elif order.category_id == 1:
            p_cost = 1200.0
        else:
            p_cost = order.price_per_unit * 0.65
        prod_cost_total = order.quantity * p_cost
        overhead = 0.1 * prod_cost_total
        order.net_profit = order.total_value - (prod_cost_total + overhead)
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)
    return order


def soft_delete_order(db: Session, order: Order) -> None:
    order.is_deleted = True
    order.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Restore inventory back
    try:
        from app.models.order import ProductCategory
        cat = db.query(ProductCategory).filter(ProductCategory.id == order.category_id).first()
        cat_name = cat.name if cat else "Silk Saree"
        restore_inventory_for_order(db, order.weaver_user_id, cat_name, order.quantity)
    except Exception as e:
        print(f"Failed to restore stock for deleted order: {e}")


def add_payment(db: Session, order: Order, data: PaymentCreate) -> Payment:
    payment = Payment(
        order_id=order.id,
        amount=data.amount,
        payment_date=data.payment_date,
        payment_type=data.payment_type,
    )
    db.add(payment)

    # Auto-update order status based on total payments
    total_paid = sum(p.amount for p in order.payments) + data.amount
    if total_paid >= order.total_value:
        order.status = "paid"
    else:
        order.status = "partially_paid"
    order.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(payment)
    return payment
