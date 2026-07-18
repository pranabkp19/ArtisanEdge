import csv
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to sys.path so we can import app modules
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.append(str(BACKEND_DIR))

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.models.user import User, WeaverProfile
from app.models.order import ProductCategory, Buyer, Order, Payment


def parse_date(date_str):
    if not date_str or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def seed():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(User).count() > 0:
            print("Database already contains data. Skipping seeding.")
            return

        print("Seeding database from seed_orders.csv...")
        csv_path = BACKEND_DIR.parent / "ml" / "data" / "seed_orders.csv"
        if not csv_path.exists():
            print(f"Error: CSV file not found at {csv_path}")
            return

        # Predefined mapping for weavers to ensure deterministic phone numbers
        weaver_phone_map = {
            "W001": "9876543201",
            "W002": "9876543202",
            "W003": "9876543203",
            "W004": "9876543204",
            "W005": "9876543205",
        }

        category_map = {}  # name -> ProductCategory
        buyer_map = {}     # buyer_id -> Buyer
        weaver_map = {}    # weaver_id -> User

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 1. Seed Product Categories
        print("Seeding product categories...")
        unique_categories = sorted(list(set(row["category"] for row in rows if row["category"])))
        for cat_name in unique_categories:
            category = ProductCategory(
                name=cat_name,
                craft_cluster="General",
                description=f"Handloom {cat_name} category"
            )
            db.add(category)
            db.flush()
            category_map[cat_name] = category

        # 2. Seed Buyers
        print("Seeding buyers...")
        unique_buyers = {}  # buyer_id -> buyer_name
        for row in rows:
            bid = row["buyer_id"]
            bname = row["buyer_name"]
            if bid and bid not in unique_buyers:
                unique_buyers[bid] = bname

        for bid, bname in unique_buyers.items():
            buyer = Buyer(
                business_name=bname,
                buyer_type="boutique",
                avg_payment_delay_days=15.0 if bid in ["B001", "B002"] else 30.0
            )
            db.add(buyer)
            db.flush()
            buyer_map[bid] = buyer

        # 3. Seed Weavers (Users & Profiles)
        print("Seeding weaver accounts...")
        unique_weavers = {}  # weaver_id -> (name, cluster)
        for row in rows:
            wid = row["weaver_id"]
            wname = row["weaver_name"]
            cluster = row["craft_cluster"]
            if wid and wid not in unique_weavers:
                unique_weavers[wid] = (wname, cluster)

        default_password_hash = hash_password("weaver123")

        for wid, (wname, cluster) in unique_weavers.items():
            phone = weaver_phone_map.get(wid, f"98765432{wid[-2:]}")
            user = User(
                phone_number=phone,
                full_name=wname,
                password_hash=default_password_hash,
                role="weaver",
                language_pref="en",
                region=cluster,
            )
            db.add(user)
            db.flush()

            profile = WeaverProfile(
                user_id=user.id,
                craft_cluster=cluster,
                avg_production_rate_per_week=5.0,
                primary_category=rows[0]["category"]  # default
            )
            db.add(profile)
            weaver_map[wid] = user

        # 4. Seed Orders & Payments
        print(f"Seeding {len(rows)} orders and payments...")
        for row in rows:
            wid = row["weaver_id"]
            bid = row["buyer_id"]
            cat_name = row["category"]

            weaver_user = weaver_map.get(wid)
            buyer = buyer_map.get(bid)
            category = category_map.get(cat_name)

            if not weaver_user:
                continue

            order = Order(
                weaver_user_id=weaver_user.id,
                buyer_id=buyer.id if buyer else None,
                category_id=category.id if category else None,
                quantity=int(row["quantity"]),
                price_per_unit=float(row["price_per_unit"]),
                total_value=float(row["total_value"]),
                order_date=parse_date(row["order_date"]),
                expected_delivery_date=parse_date(row["expected_delivery_date"]),
                expected_payment_date=parse_date(row["expected_payment_date"]),
                status=row["status"],
                advance_amount=float(row["advance_amount"]) if row["advance_amount"] else 0.0,
            )
            db.add(order)
            db.flush()

            # Seed Payments if paid or partially paid
            advance_amt = float(row["advance_amount"]) if row["advance_amount"] else 0.0
            actual_pay_date = parse_date(row["actual_payment_date"])

            # Add advance payment
            if advance_amt > 0:
                adv_payment = Payment(
                    order_id=order.id,
                    amount=advance_amt,
                    payment_date=order.order_date,
                    payment_type="advance"
                )
                db.add(adv_payment)

            # Add final payment
            if order.status == "paid":
                final_amt = order.total_value - advance_amt
                pay_date = actual_pay_date if actual_pay_date else order.expected_payment_date
                final_payment = Payment(
                    order_id=order.id,
                    amount=final_amt,
                    payment_date=pay_date,
                    payment_type="full" if advance_amt == 0 else "partial"
                )
                db.add(final_payment)
            elif order.status == "partially_paid":
                # Assume partial paid amount is half of remaining
                partial_amt = (order.total_value - advance_amt) / 2
                pay_date = actual_pay_date if actual_pay_date else order.expected_payment_date
                partial_payment = Payment(
                    order_id=order.id,
                    amount=partial_amt,
                    payment_date=pay_date,
                    payment_type="partial"
                )
                db.add(partial_payment)

        db.commit()
        print("Database seeded successfully!")
        
        # Output credentials for testing
        print("\nTest Weaver Accounts Seeded:")
        for wid, user in weaver_map.items():
            print(f"- {user.full_name}: Phone = {user.phone_number}, Password = weaver123, Region = {user.region}")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()
