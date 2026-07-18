from datetime import date, datetime
from pydantic import BaseModel
from app.schemas.orders import CategoryOut


class ForecastOut(BaseModel):
    id: int
    user_id: int
    category_id: int
    forecast_type: str
    period_start: date
    period_end: date
    predicted_demand_index: float
    confidence_score: float
    confidence_label: str
    explanation_text: str | None = None
    model_version: str
    generated_at: datetime

    category: CategoryOut | None = None

    model_config = {"from_attributes": True}
