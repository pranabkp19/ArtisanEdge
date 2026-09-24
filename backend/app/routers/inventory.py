from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.inventory import Inventory
from app.models.forecast import Forecast
from app.schemas.inventory import InventoryOut, PlannerResponse, StockUpdate, MaterialCreate
from app.services.planner import calculate_material_requirements

router = APIRouter(prefix="/inventory", tags=["Inventory & Materials"])


def ensure_default_inventory(db: Session, user_id: int) -> list[Inventory]:
    """Check if the user has stock records; if empty, return empty list (no seeding)."""
    return db.query(Inventory).filter(Inventory.user_id == user_id).all()


@router.get("", response_model=list[InventoryOut])
def get_raw_inventory(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve raw stock levels directly from SQLite."""
    return ensure_default_inventory(db, current_user.id)


@router.get("/planner", response_model=PlannerResponse)
def get_inventory_planner(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve 3-month raw material needs mapped to the user's active forecasts alongside current stocks."""
    # Ensure default inventories exist
    inventory_items = ensure_default_inventory(db, current_user.id)

    # Fetch cached forecasts
    forecasts = db.query(Forecast).filter(Forecast.user_id == current_user.id).all()

    # Calculate material requirements
    reqs = calculate_material_requirements(forecasts)

    return PlannerResponse(
        materials_required={
            "silk_yarn": reqs["silk_yarn"],
            "cotton_yarn": reqs["cotton_yarn"],
            "dyes": reqs["dyes"],
        },
        breakdown=reqs["breakdown"],
        current_inventory=[InventoryOut.model_validate(item) for item in inventory_items],
    )


from pydantic import BaseModel, Field
from urllib.parse import unquote
from sqlalchemy import func

class PutStockUpdate(BaseModel):
    current_stock: float = Field(..., ge=0)


@router.put("/{material_name}", response_model=InventoryOut)
@router.put("/{material_name}/", response_model=InventoryOut)
def update_stock_by_name(
    material_name: str,
    body: PutStockUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update current stock level for a material by name."""
    # Ensure default inventories exist
    ensure_default_inventory(db, current_user.id)

    # Decode and sanitize the incoming material name
    decoded_name = unquote(material_name).strip().lower()

    item = (
        db.query(Inventory)
        .filter(
            Inventory.user_id == current_user.id,
            func.lower(func.trim(Inventory.material_name)) == decoded_name
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory record for '{material_name}' not found",
        )

    item.current_stock = body.current_stock
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{inventory_id:int}", response_model=InventoryOut)
def update_stock_level(
    inventory_id: int,
    body: StockUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update current stock and safety buffers for a raw material record."""
    item = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not item or item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )

    item.current_stock = body.current_stock
    if body.safety_buffer is not None:
        item.safety_buffer = body.safety_buffer

    db.commit()
    db.refresh(item)
    return item


@router.post("", response_model=InventoryOut)
@router.post("/", response_model=InventoryOut)
def add_new_material(
    body: MaterialCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Add a new raw material to the weaver's inventory."""
    sanitized_name = body.material_name.strip()
    exists = (
        db.query(Inventory)
        .filter(
            Inventory.user_id == current_user.id,
            func.lower(func.trim(Inventory.material_name)) == sanitized_name.lower()
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Material '{sanitized_name}' already exists in your inventory.",
        )

    new_item = Inventory(
        user_id=current_user.id,
        material_name=sanitized_name,
        current_stock=body.current_stock,
        safety_buffer=body.safety_buffer,
        unit=body.unit,
        production_cost=body.production_cost,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/{inventory_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    inventory_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a raw material record from the user's inventory planner."""
    item = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not item or item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )
    db.delete(item)
    db.commit()
