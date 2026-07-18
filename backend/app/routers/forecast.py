import sys
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

# Append paths to allow importing predict_engine
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "ml" / "pipeline"))

try:
    from predict_engine import PredictLoomEngine
except ImportError:
    PredictLoomEngine = None

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.forecast import Forecast
from app.schemas.forecast import ForecastOut

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/me", response_model=list[ForecastOut])
def get_my_forecasts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve all cached forecasts for the current authenticated weaver."""
    forecasts = (
        db.query(Forecast)
        .filter(Forecast.user_id == current_user.id)
        .options(joinedload(Forecast.category))
        .order_by(Forecast.period_start.asc(), Forecast.predicted_demand_index.desc())
        .all()
    )
    return forecasts


@router.post("/regenerate", status_code=status.HTTP_200_OK)
def regenerate_forecasts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Trigger the ML forecasting engine to recalculate monthly demands."""
    if PredictLoomEngine is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Predictive engine pipeline is not available on backend path.",
        )
    try:
        engine = PredictLoomEngine()
        count = engine.run_forecasts()
        return {
            "message": "Successfully regenerated forecasts and loaded to SQLite.",
            "rows_created": count,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecasting pipeline runtime error: {e}",
        )


def get_predict_data(current_user: User, db: Session):
    from app.models.inventory import Inventory
    
    # 1. Query the database for the active user's inventory materials
    user_materials = db.query(Inventory).filter(Inventory.user_id == current_user.id).all()
    
    # If the user has no materials, return an empty forecast list
    if not user_materials:
        return {
            "status": "success",
            "forecast": []
        }
        
    # 2. Otherwise, dynamically generate simulated 3-month forecasts for actual database materials
    forecast_list = []
    for idx, mat in enumerate(user_materials):
        # Calculate a simulated demand: safety buffer * 1.35 (seasonal multiplier index)
        # Rounded to 1 decimal place
        buffer = float(mat.safety_buffer or 5.0)
        predicted_demand = round(buffer * 1.35 * 10) / 10
        if predicted_demand == 0:
            predicted_demand = 15.0
            
        # Confidence score slightly indexed
        confidence = round((0.88 + (idx % 5) * 0.02) * 100) / 100
        
        forecast_list.append({
            "material_name": mat.material_name,
            "predicted_demand": predicted_demand,
            "confidence_score": confidence
        })
        
    return {
        "status": "success",
        "forecast": forecast_list
    }


@router.get("/predict")
def predict_raw_material_demand(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Calculate the 3-month production demand cycles for raw materials."""
    return get_predict_data(current_user, db)
