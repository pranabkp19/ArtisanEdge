from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.orders import (
    OrderCreate,
    OrderListResponse,
    OrderOut,
    OrderUpdate,
    PaymentCreate,
    PaymentOut,
    CategoryOut,
    BuyerOut,
)
from app.services.order_service import (
    add_payment,
    create_order,
    get_order_by_id,
    get_orders,
    soft_delete_order,
    update_order,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=OrderListResponse)
def list_orders(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    category_id: int | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List orders for the current user (filtered, paginated)."""
    # If user is DemoArtisan and has no transactions, auto-seed 18 records in a single transaction commit
    if current_user.full_name == "DemoArtisan":
        from app.models.order import Order
        order_count = db.query(Order).filter(Order.weaver_user_id == current_user.id, Order.is_deleted.is_(False)).count()
        if order_count == 0:
            from datetime import date
            from app.models.order import ProductCategory, Buyer
            
            categories = db.query(ProductCategory).all()
            silk_cat = next((c for c in categories if "silk" in c.name.lower()), categories[0] if categories else None)
            cotton_cat = next((c for c in categories if "cotton" in c.name.lower()), categories[1] if len(categories) > 1 else (categories[0] if categories else None))
            
            buyer = db.query(Buyer).first()
            buyer_id = buyer.id if buyer else 1
            
            if silk_cat and cotton_cat:
                demo_tx = [
                    # Date, Category, Qty, Price, Status, Advance
                    ("2026-01-10", silk_cat.id, 3, 6000.0, "paid", 6000.0 * 3),
                    ("2026-01-20", cotton_cat.id, 5, 3000.0, "pending", 0.0),
                    
                    ("2026-02-08", silk_cat.id, 4, 6000.0, "overdue", 500.0),
                    ("2026-02-22", cotton_cat.id, 6, 3000.0, "paid", 3000.0 * 6),
                    
                    ("2026-03-05", silk_cat.id, 5, 6200.0, "pending", 1000.0),
                    ("2026-03-18", cotton_cat.id, 7, 3100.0, "overdue", 0.0),
                    
                    ("2026-04-12", silk_cat.id, 6, 6250.0, "paid", 6250.0 * 6),
                    ("2026-04-25", cotton_cat.id, 9, 3150.0, "pending", 200.0),
                    
                    ("2026-05-02", silk_cat.id, 7, 6500.0, "overdue", 150.0),
                    ("2026-05-15", cotton_cat.id, 10, 3200.0, "paid", 3200.0 * 10),
                    
                    ("2026-06-04", silk_cat.id, 9, 6500.0, "pending", 500.0),
                    ("2026-06-18", cotton_cat.id, 11, 3200.0, "overdue", 0.0),
                    
                    # Additional transactions
                    ("2026-01-15", silk_cat.id, 2, 6100.0, "paid", 6100.0 * 2),
                    ("2026-02-15", cotton_cat.id, 1, 3050.0, "pending", 100.0),
                    ("2026-03-25", silk_cat.id, 3, 6300.0, "overdue", 0.0),
                    ("2026-04-18", cotton_cat.id, 2, 3100.0, "paid", 3100.0 * 2),
                    ("2026-05-28", silk_cat.id, 4, 6400.0, "pending", 300.0),
                    ("2026-06-25", cotton_cat.id, 3, 3250.0, "overdue", 0.0),
                ]
                
                db_orders = []
                for dt_str, cat_id, qty, price, status_str, adv in demo_tx:
                    order_date = date.fromisoformat(dt_str)
                    db_orders.append(
                        Order(
                            weaver_user_id=current_user.id,
                            category_id=cat_id,
                            buyer_id=buyer_id,
                            quantity=qty,
                            price_per_unit=price,
                            total_value=qty * price,
                            order_date=order_date,
                            expected_delivery_date=order_date,
                            expected_payment_date=order_date,
                            advance_amount=adv,
                            status=status_str,
                        )
                    )
                db.add_all(db_orders)
                db.commit()

    orders, total = get_orders(
        db, current_user.id,
        status_filter=status_filter,
        category_id=category_id,
        page=page,
        per_page=per_page,
    )
    return OrderListResponse(
        total=total, page=page, per_page=per_page,
        orders=[OrderOut.model_validate(o) for o in orders],
    )


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_new_order(
    body: OrderCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Create a new order for the current weaver."""
    order = create_order(db, current_user.id, body)
    return OrderOut.model_validate(order)


@router.get("/categories", response_model=list[CategoryOut])
def get_categories(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Retrieve all product categories."""
    from app.models.order import ProductCategory
    return db.query(ProductCategory).all()


@router.get("/buyers", response_model=list[BuyerOut])
def get_buyers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)]
):
    """Retrieve all buyers."""
    from app.models.order import Buyer
    return db.query(Buyer).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_single_order(

    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get a single order by ID (must be owned by the current user)."""
    order = get_order_by_id(db, order_id)
    if not order or order.weaver_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderOut.model_validate(order)


@router.patch("/{order_id}", response_model=OrderOut)
def update_existing_order(
    order_id: int,
    body: OrderUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Update fields on an existing order."""
    order = get_order_by_id(db, order_id)
    if not order or order.weaver_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    updated = update_order(db, order, body)
    return OrderOut.model_validate(updated)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Soft-delete an order (sets is_deleted=True, retains for audit)."""
    order = get_order_by_id(db, order_id)
    if not order or order.weaver_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    soft_delete_order(db, order)


@router.post("/{order_id}/payments", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def log_payment(
    order_id: int,
    body: PaymentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Log a payment against an order. Auto-updates order status."""
    order = get_order_by_id(db, order_id)
    if not order or order.weaver_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    payment = add_payment(db, order, body)
    return PaymentOut.model_validate(payment)


transactions_router = APIRouter(prefix="/transactions", tags=["Transactions"])


@transactions_router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Delete a transaction ledger record (restoring its corresponding inventory raw material levels)."""
    order = get_order_by_id(db, transaction_id)
    if not order or order.weaver_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction record not found",
        )
    soft_delete_order(db, order)
