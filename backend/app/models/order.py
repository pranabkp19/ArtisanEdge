from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductCategory(Base):
    """Handloom product categories (Silk Saree, Cotton Saree, Stole, etc.)."""
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    craft_cluster: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    orders: Mapped[list["Order"]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<ProductCategory id={self.id} name={self.name}>"


class Buyer(Base):
    """Buyer profiles — boutiques, exporters, e-commerce aggregators, etc."""
    __tablename__ = "buyers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    business_name: Mapped[str] = mapped_column(String(120), nullable=False)
    buyer_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
        comment="boutique | exporter | e_commerce | individual | government",
    )
    avg_payment_delay_days: Mapped[float] = mapped_column(Float, default=30.0)

    # Relationships
    orders: Mapped[list["Order"]] = relationship(back_populates="buyer")

    def __repr__(self) -> str:
        return f"<Buyer id={self.id} name={self.business_name}>"


class Order(Base):
    """Order ledger — the core data source for the forecasting engine."""
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_weaver_date", "weaver_user_id", "order_date"),
        Index("ix_orders_category_date", "category_id", "order_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    weaver_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    cooperative_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buyer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("buyers.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("product_categories.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending | confirmed | in_production | delivered | partially_paid | paid | overdue | cancelled",
    )
    advance_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    weaver: Mapped["User"] = relationship(
        "User", back_populates="orders", foreign_keys=[weaver_user_id]
    )
    buyer: Mapped["Buyer | None"] = relationship(back_populates="orders")
    category: Mapped["ProductCategory | None"] = relationship(back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} weaver={self.weaver_user_id} status={self.status}>"


class Payment(Base):
    """Individual payment records against an order."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="full",
        comment="advance | partial | full",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} order_id={self.order_id} amount={self.amount}>"
