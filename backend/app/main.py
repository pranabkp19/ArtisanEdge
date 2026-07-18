from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION
from app.db.base import Base
from app.db.session import engine
from app.routers import auth, orders, forecast, inventory

# Import models so Base.metadata registers all tables
import app.models  # noqa: F401


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI instance."""
    application = FastAPI(
        title=APP_TITLE,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS (allow frontend dev server) ─────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Create tables ────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)

    # ── Register routers under /api/v1 ───────────────────────────────
    api_prefix = "/api/v1"
    application.include_router(auth.router, prefix=api_prefix)
    application.include_router(orders.router, prefix=api_prefix)
    application.include_router(orders.transactions_router, prefix=api_prefix)
    application.include_router(forecast.router, prefix=api_prefix)
    application.include_router(inventory.router, prefix=api_prefix)

    from typing import Annotated
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from app.core.dependencies import get_current_user
    from app.db.session import get_db
    from app.models.user import User

    @application.get("/api/forecast/predict", tags=["Forecast"])
    def predict_direct(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
    ):
        from app.routers.forecast import get_predict_data
        return get_predict_data(current_user, db)


    @application.get("/", tags=["Health"])
    def health_check():
        return {"status": "healthy", "app": APP_TITLE, "version": APP_VERSION}


    return application


app = create_app()
