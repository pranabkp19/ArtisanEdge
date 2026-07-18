from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Core user account — all roles share this table."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="weaver",
        comment="weaver | cooperative_admin | buyer | officer | ngo | admin",
    )
    language_pref: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    weaver_profile: Mapped["WeaverProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order", back_populates="weaver", foreign_keys="Order.weaver_user_id"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} phone={self.phone_number} role={self.role}>"


class WeaverProfile(Base):
    """Extended profile for users with role='weaver'."""
    __tablename__ = "weaver_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    craft_cluster: Mapped[str | None] = mapped_column(String(50), nullable=True)
    avg_production_rate_per_week: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    onboarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="weaver_profile")

    def __repr__(self) -> str:
        return f"<WeaverProfile user_id={self.user_id} cluster={self.craft_cluster}>"
