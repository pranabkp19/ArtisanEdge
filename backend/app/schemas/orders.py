from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator


# ── Request Schemas ──────────────────────────────────────────────

class OrderCreate(BaseModel):
    """Body for POST /orders."""
    category_id: int | None = None
    buyer_id: int | None = None
    quantity: int = Field(..., gt=0, description="Must be > 0")
    price_per_unit: float = Field(..., gt=0, description="Must be > 0")
    order_date: date
    expected_delivery_date: date | None = None
    expected_payment_date: date | None = None
    advance_amount: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def dates_must_be_logical(self):
        if self.expected_delivery_date and self.expected_delivery_date < self.order_date:
            raise ValueError("expected_delivery_date must be >= order_date")
        if self.expected_payment_date and self.expected_payment_date < self.order_date:
            raise ValueError("expected_payment_date must be >= order_date")
        return self


class OrderUpdate(BaseModel):
    """Body for PATCH /orders/{id}."""
    category_id: int | None = None
    buyer_id: int | None = None
    quantity: int | None = Field(default=None, gt=0)
    price_per_unit: float | None = Field(default=None, gt=0)
    status: str | None = None
    expected_delivery_date: date | None = None
    expected_payment_date: date | None = None
    advance_amount: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def status_must_be_valid(self):
        if self.status is not None:
            allowed = {
                "pending", "confirmed", "in_production", "delivered",
                "partially_paid", "paid", "overdue", "cancelled",
            }
            if self.status not in allowed:
                raise ValueError(f"Status must be one of {allowed}")
        return self


class PaymentCreate(BaseModel):
    """Body for POST /orders/{id}/payments."""
    amount: float = Field(..., gt=0)
    payment_date: date
    payment_type: str = Field(
        default="full",
        description="advance | partial | full",
    )


# ── Response Schemas ─────────────────────────────────────────────

class CategoryOut(BaseModel):
    id: int
    name: str
    craft_cluster: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class BuyerOut(BaseModel):
    id: int
    business_name: str
    buyer_type: str | None = None
    avg_payment_delay_days: float

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_date: date
    payment_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    weaver_user_id: int
    cooperative_id: int | None = None
    buyer_id: int | None = None
    category_id: int | None = None
    quantity: int
    price_per_unit: float
    total_value: float
    net_profit: float
    order_date: date
    expected_delivery_date: date | None = None
    expected_payment_date: date | None = None
    status: str
    advance_amount: float
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    # Nested relations (optional — populated when joined)
    category: CategoryOut | None = None
    buyer: BuyerOut | None = None
    payments: list[PaymentOut] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    """Paginated order list."""
    total: int
    page: int
    per_page: int
    orders: list[OrderOut]
