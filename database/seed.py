"""Generate ~12 months of realistic fake data. Run after schema.sql.
Usage: python database/seed.py
"""
import os, random
from datetime import datetime, timedelta
import pymysql
from faker import Faker
from dotenv import load_dotenv

load_dotenv()
fake = Faker("en_IN")
random.seed(42)

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "smart_business"),
    autocommit=False,
)
cur = conn.cursor()

CATEGORIES = ["Electronics", "Groceries", "Clothing", "Home & Kitchen", "Stationery", "Beauty"]
REGIONS = {"South": ["Hyderabad", "Bengaluru", "Chennai"], "North": ["Delhi", "Jaipur"],
           "West": ["Mumbai", "Pune"], "East": ["Kolkata", "Bhubaneswar"]}
END = datetime.now()
START = END - timedelta(days=365)

# Categories, suppliers
cur.executemany("INSERT INTO categories (name) VALUES (%s)", [(c,) for c in CATEGORIES])
cur.executemany("INSERT INTO suppliers (name, email, phone, city) VALUES (%s,%s,%s,%s)",
                [(fake.company(), fake.company_email(), fake.phone_number()[:30], fake.city()) for _ in range(8)])

# Products
products = []
for i in range(1, 61):
    cost = round(random.uniform(50, 2000), 2)
    price = round(cost * random.uniform(1.2, 1.6), 2)
    products.append((f"SKU{i:04d}", f"{fake.word().title()} {fake.word().title()}",
                     random.randint(1, len(CATEGORIES)), random.randint(1, 8),
                     cost, price, random.choice([10, 15, 20, 30])))
cur.executemany("INSERT INTO products (sku,name,category_id,supplier_id,cost_price,unit_price,reorder_level) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)", products)
price_of = {i + 1: p[5] for i, p in enumerate(products)}

# Customers
customers = []
for _ in range(250):
    region = random.choice(list(REGIONS))
    customers.append((fake.name(), fake.email(), fake.phone_number()[:30],
                      random.choice(REGIONS[region]), region,
                      START + timedelta(days=random.randint(0, 300))))
cur.executemany("INSERT INTO customers (name,email,phone,city,region,created_at) VALUES (%s,%s,%s,%s,%s,%s)", customers)

# Opening stock
cur.executemany("INSERT INTO inventory_movements (product_id,change_qty,movement_type,created_at) VALUES (%s,%s,'purchase',%s)",
                [(pid, random.randint(150, 400), START) for pid in range(1, 61)])

# Orders with mild upward trend + festive-season bump (Oct-Nov)
day = START
order_id = 0
while day <= END:
    growth = 1 + (day - START).days / 365 * 0.5
    festive = 1.5 if day.month in (10, 11) else 1.0
    for _ in range(max(0, int(random.gauss(8, 2) * growth * festive))):
        order_id += 1
        ts = day.replace(hour=random.randint(9, 21), minute=random.randint(0, 59))
        status = random.choices(["completed", "cancelled", "returned"], [92, 5, 3])[0]
        items = random.sample(range(1, 61), random.randint(1, 4))
        lines = [(pid, random.randint(1, 4), price_of[pid]) for pid in items]
        total = round(sum(q * pr for _, q, pr in lines), 2)
        cur.execute("INSERT INTO orders (customer_id,order_date,status,total_amount) VALUES (%s,%s,%s,%s)",
                    (random.randint(1, 250), ts, status, total))
        oid = cur.lastrowid
        cur.executemany("INSERT INTO order_items (order_id,product_id,quantity,unit_price) VALUES (%s,%s,%s,%s)",
                        [(oid, pid, q, pr) for pid, q, pr in lines])
        if status == "completed":
            cur.executemany("INSERT INTO inventory_movements (product_id,change_qty,movement_type,reference_id,created_at) "
                            "VALUES (%s,%s,'sale',%s,%s)", [(pid, -q, oid, ts) for pid, q, _ in lines])
    # Restock roughly weekly
    if day.weekday() == 0:
        cur.executemany("INSERT INTO inventory_movements (product_id,change_qty,movement_type,created_at) "
                        "VALUES (%s,%s,'purchase',%s)",
                        [(pid, random.randint(30, 120), day) for pid in random.sample(range(1, 61), 20)])
    day += timedelta(days=1)

conn.commit()
print(f"Seeded {order_id} orders, 60 products, 250 customers.")
