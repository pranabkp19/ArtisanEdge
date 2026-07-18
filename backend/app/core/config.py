import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
DB_PATH = BASE_DIR / "handloom.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# ── JWT Settings ─────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "artisanedge-hackathon-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ── App Metadata ─────────────────────────────────────────────────
APP_TITLE = "ArtisanEdge API"
APP_DESCRIPTION = "Demand forecasting & income stability platform for handloom weavers"
APP_VERSION = "0.1.0"
