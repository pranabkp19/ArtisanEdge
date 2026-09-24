from datetime import datetime, timezone
from sqlalchemy import Float, ForeignKey, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Inventory(Base):
    """Weaver's current stock levels and safety buffers for raw materials."""
    __tablename__ = "inventories"
    __table_args__ = (UniqueConstraint("user_id", "material_name", name="uq_user_material"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    material_name: Mapped[str] = mapped_column(String(50), nullable=False)
    current_stock: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    safety_buffer: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    unit: Mapped[str] = mapped_column(String(10), nullable=False, default="kg")
    production_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Inventory id={self.id} user={self.user_id} material={self.material_name} stock={self.current_stock}>"
