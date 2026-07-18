# Import all models here so that Base.metadata knows about them
# when we call create_all() during initialization.
from app.models.user import User, WeaverProfile  # noqa: F401
from app.models.order import ProductCategory, Buyer, Order, Payment  # noqa: F401
from app.models.forecast import Forecast, ProductionPlan  # noqa: F401
from app.models.inventory import Inventory  # noqa: F401


