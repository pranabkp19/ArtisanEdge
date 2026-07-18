from datetime import datetime
from pydantic import BaseModel, Field


class InventoryOut(BaseModel):
    id: int
    user_id: int
    material_name: str
    current_stock: float
    safety_buffer: float
    unit: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class StockUpdate(BaseModel):
    current_stock: float = Field(..., ge=0)
    safety_buffer: float | None = Field(default=None, ge=0)


class MaterialCreate(BaseModel):
    material_name: str = Field(..., min_length=1, max_length=50)
    current_stock: float = Field(..., ge=0)
    safety_buffer: float = Field(..., ge=0)
    unit: str = Field(default="kg", max_length=10)


class MaterialRequirementDetail(BaseModel):
    category_id: int
    category_name: str
    period_start: str
    period_end: str
    quantity: float
    silk_yarn: float
    cotton_yarn: float
    dyes: float


class PlannerResponse(BaseModel):
    materials_required: dict  # {"silk_yarn": float, "cotton_yarn": float, "dyes": float}
    breakdown: list[dict]
    current_inventory: list[InventoryOut]
