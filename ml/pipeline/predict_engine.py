import os
import sys
import sqlite3
import warnings
from datetime import datetime, date, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Add the backend directory to sys.path so we can import app modules
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.db.session import SessionLocal
from app.models.user import User, WeaverProfile
from app.models.order import Order, ProductCategory, Buyer
from app.models.forecast import Forecast

# Suppress ConvergenceWarning and other statsmodels warnings
warnings.filterwarnings("ignore")


class PredictLoomEngine:
    def __init__(self):
        self.db_path = PROJECT_ROOT / "backend" / "handloom.db"
        self.calendar_path = PROJECT_ROOT / "ml" / "data" / "seasonal_calendar.csv"

    def load_seasonal_calendar(self):
        """Load the seasonal calendar dataset."""
        if not self.calendar_path.exists():
            raise FileNotFoundError(f"Seasonal calendar not found at {self.calendar_path}")
        return pd.read_csv(self.calendar_path)

    def get_orders_df(self):
        """Fetch all non-deleted orders from SQLite into a Pandas DataFrame."""
        conn = sqlite3.connect(str(self.db_path))
        query = """
            SELECT o.id, o.weaver_user_id, o.category_id, o.quantity, o.price_per_unit, o.total_value, 
                   o.order_date, o.status, u.region as craft_cluster
            FROM orders o
            JOIN users u ON o.weaver_user_id = u.id
            WHERE o.is_deleted = 0
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        df["order_date"] = pd.to_datetime(df["order_date"])
        return df

    def cap_outliers_iqr(self, series: pd.Series, window: int = 6) -> pd.Series:
        """Cap outliers using rolling IQR to prevent single large spikes from skewing forecasts."""
        if len(series) < window:
            # Fallback to global IQR if series is short
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            upper_bound = q3 + 1.5 * iqr
            return series.clip(upper=upper_bound)
        
        # Rolling IQR capping
        rolling_q1 = series.rolling(window, min_periods=1).quantile(0.25)
        rolling_q3 = series.rolling(window, min_periods=1).quantile(0.75)
        rolling_iqr = rolling_q3 - rolling_q1
        upper_bounds = rolling_q3 + 1.5 * rolling_iqr
        return series.combine(upper_bounds, min)

    def prepare_time_series(self, df: pd.DataFrame, weaver_id: int, category_id: int):
        """Aggregate, outlier-cap, and zero-fill time series to monthly buckets."""
        # Filter for specific weaver & category
        sub_df = df[(df["weaver_user_id"] == weaver_id) & (df["category_id"] == category_id)].copy()
        
        # Monthly date range from July 2024 to June 2026 (the standard 24-month seed span)
        full_idx = pd.date_range(start="2024-07-01", end="2026-06-01", freq="MS")
        
        if sub_df.empty:
            # If empty, return all zeros
            return pd.Series(0.0, index=full_idx), 0

        # Set date index and resample to monthly sum
        sub_df.set_index("order_date", inplace=True)
        ts = sub_df["quantity"].resample("MS").sum()
        
        # Reindex to force full 24-month index and zero-fill missing months
        ts = ts.reindex(full_idx, fill_value=0.0)
        
        # Count non-zero months
        non_zero_months = int((ts > 0).sum())
        
        # Cap outliers
        ts_capped = self.cap_outliers_iqr(ts)
        return ts_capped, non_zero_months

    def generate_explanation(self, category_name: str, trend: float, next_multiplier: float, next_festival: str) -> str:
        """Formulate explanation copy based on forecast direction and festival cues."""
        direction = "increase" if trend > 0 else "decrease"
        if next_multiplier > 1.2:
            return (
                f"Demand for {category_name} is expected to see a strong seasonal {direction} "
                f"due to the upcoming {next_festival} window. Consider stocking raw yarn materials in advance."
            )
        elif next_multiplier < 0.9:
            return (
                f"Demand for {category_name} is expected to decline temporarily during the summer/monsoon lull. "
                f"Recommended to focus on diversifying patterns or building safety buffers."
            )
        else:
            return (
                f"Demand for {category_name} is projected to remain stable, matching typical seasonal baselines "
                f"learned from your historical order records."
            )

    def run_forecasts(self):
        """Run the time-series forecasting loop and write predictions to SQLite."""
        from app.db.base import Base
        from app.db.session import engine
        Base.metadata.create_all(bind=engine)

        db = SessionLocal()
        try:
            print("ML Engine: Starting forecasting run...")
            
            # 1. Clear old forecasts to prevent duplication
            db.query(Forecast).delete()

            db.commit()

            # 2. Load configurations & data
            calendar_df = self.load_seasonal_calendar()
            orders_df = self.get_orders_df()
            
            weavers = db.query(User).filter(User.role == "weaver", User.is_active == True).all()
            categories = db.query(ProductCategory).all()
            
            # Forecast periods (next 3 months: July, August, September 2026)
            forecast_dates = pd.date_range(start="2026-07-01", end="2026-09-01", freq="MS")
            
            # Precompute cluster-level fallback averages
            # Category -> Month (1-12) -> Average Quantity
            cluster_averages = {}
            if not orders_df.empty:
                orders_df["month"] = orders_df["order_date"].dt.month
                # Group by category & month to get average monthly quantity per weaver
                grouped = orders_df.groupby(["category_id", "month", "weaver_user_id"])["quantity"].sum().reset_index()
                cluster_averages = grouped.groupby(["category_id", "month"])["quantity"].mean().to_dict()

            total_generated = 0

            for weaver in weavers:
                for category in categories:
                    # Retrieve prepared time series and count of data points
                    ts, non_zero_count = self.prepare_time_series(orders_df, weaver.id, category.id)
                    
                    # Target category details
                    cat_name = category.name
                    forecast_results = []
                    explanation = ""
                    conf_score = 0.8
                    conf_label = "Medium"
                    model_type = "fallback"

                    # Fetch festival exogenous multipliers for forecast months
                    exog_multipliers = []
                    exog_festivals = []
                    for d in forecast_dates:
                        m_row = calendar_df[calendar_df["month"] == d.month]
                        mult = float(m_row["demand_multiplier"].values[0]) if not m_row.empty else 1.0
                        fest = str(m_row["festival_name"].values[0]) if not m_row.empty else "Normal Season"
                        exog_multipliers.append(mult)
                        exog_festivals.append(fest)

                    # Tier 2: SARIMAX (6+ months of non-zero data)
                    if non_zero_count >= 6:
                        try:
                            # Build exogenous series matching historical index months (1 to 12)
                            hist_months = ts.index.month
                            hist_exog = []
                            for m in hist_months:
                                m_row = calendar_df[calendar_df["month"] == m]
                                hist_exog.append(float(m_row["demand_multiplier"].values[0]) if not m_row.empty else 1.0)
                            
                            # Fit SARIMAX (p=1, d=0, q=0)
                            model = SARIMAX(ts, exog=hist_exog, order=(1, 0, 0), enforce_stationarity=False)
                            fitted = model.fit(disp=False)
                            
                            # Predict 3 months using exogenous multipliers
                            pred = fitted.forecast(steps=3, exog=exog_multipliers)
                            forecast_results = pred.clip(lower=0).tolist()
                            
                            # Calculate trend direction
                            trend = forecast_results[-1] - ts.iloc[-1]
                            explanation = self.generate_explanation(cat_name, trend, exog_multipliers[0], exog_festivals[0])
                            
                            conf_score = 0.85
                            conf_label = "High"
                            model_type = "individual_sarimax"
                        except Exception as e:
                            # Fallback if SARIMAX fails to fit
                            print(f"Warning: SARIMAX failed for weaver {weaver.id}, cat {category.id}: {e}")
                            non_zero_count = 5  # Push to Tier 1 HW fallback

                    # Tier 1: Holt-Winters (3 to 6 months of data)
                    if (3 <= non_zero_count < 6) or (not forecast_results and 3 <= non_zero_count):
                        try:
                            # Fit Holt-Winters Exponential Smoothing (no seasonality if < 12 points)
                            # Since we resampled to 24 continuous months, we can add additive seasonality
                            model = ExponentialSmoothing(
                                ts, trend="add", seasonal="add", seasonal_periods=12,
                                initialization_method="heuristic"
                            )
                            fitted = model.fit()
                            pred = fitted.forecast(steps=3)
                            
                            forecast_results = pred.clip(lower=0).tolist()
                            trend = forecast_results[-1] - ts.iloc[-1]
                            explanation = self.generate_explanation(cat_name, trend, exog_multipliers[0], exog_festivals[0])
                            
                            conf_score = 0.70
                            conf_label = "Medium"
                            model_type = "individual_holtwinters"
                        except Exception as e:
                            print(f"Warning: Holt-Winters failed for weaver {weaver.id}, cat {category.id}: {e}")

                    # Fallback (0 to 3 months of data, or if both models failed)
                    if not forecast_results:
                        # Use average historical demand for this category in the same cluster/month, scaled by multiplier
                        forecast_results = []
                        for idx, d in enumerate(forecast_dates):
                            # Default base quantity if database averages are empty
                            base_qty = cluster_averages.get((category.id, d.month), 4.0)
                            # Apply the multiplier
                            forecast_results.append(max(0.5, base_qty * exog_multipliers[idx]))
                        
                        explanation = (
                            f"Showing estimated demand for {cat_name} based on regional community "
                            f"averages since your sales ledger history is under 3 months."
                        )
                        conf_score = 0.50
                        conf_label = "Low"
                        model_type = "cluster_fallback"

                    # 3. Write predictions to SQLite database
                    for idx, d in enumerate(forecast_dates):
                        forecast_row = Forecast(
                            user_id=weaver.id,
                            category_id=category.id,
                            forecast_type=model_type,
                            period_start=d.date(),
                            period_end=(d + pd.offsets.MonthEnd(0)).date(),
                            predicted_demand_index=round(float(forecast_results[idx]), 2),
                            confidence_score=conf_score,
                            confidence_label=conf_label,
                            explanation_text=explanation,
                            model_version="1.0.0"
                        )
                        db.add(forecast_row)
                        total_generated += 1

            db.commit()
            print(f"ML Engine: Pipeline completed successfully. Generated {total_generated} forecast rows.")
            return total_generated

        except Exception as e:
            db.rollback()
            print(f"Error executing ML forecasting pipeline: {e}")
            raise e
        finally:
            db.close()


if __name__ == "__main__":
    engine = PredictLoomEngine()
    engine.run_forecasts()
