import os
from typing import Optional

import pymysql
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="Smart Business Analytics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "smart_business"),
        cursorclass=pymysql.cursors.DictCursor,
    )


def run_query(sql, params=None):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchall()
    finally:
        conn.close()


# Every analytics query reads from the same joined tables
BASE = """
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    JOIN products p ON p.id = oi.product_id
"""


def order_filters(start, end, category_id):
    """Build a WHERE clause and its parameters from the dashboard filters."""
    where = ["o.status = 'completed'"]
    params = []
    if start:
        where.append("o.order_date >= %s")
        params.append(start)
    if end:
        where.append("o.order_date < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(end)
    if category_id:
        where.append("p.category_id = %s")
        params.append(category_id)
    return " AND ".join(where), params


@app.get("/health")
def health():
    return {"status": "ok", **run_query("SELECT COUNT(*) AS orders FROM orders")[0]}


@app.get("/api/categories")
def categories():
    return run_query("SELECT id, name FROM categories ORDER BY name")


@app.get("/api/kpis")
def kpis(start: Optional[str] = None, end: Optional[str] = None,
         category_id: Optional[int] = None):
    where, params = order_filters(start, end, category_id)
    rows = run_query(f"""
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS revenue,
               COUNT(DISTINCT o.id) AS orders,
               COALESCE(SUM(oi.quantity * oi.unit_price)
                        / NULLIF(COUNT(DISTINCT o.id), 0), 0) AS avg_order_value
        {BASE} WHERE {where}
    """, params)
    return rows[0]


@app.get("/api/revenue-trend")
def revenue_trend(start: Optional[str] = None, end: Optional[str] = None,
                  category_id: Optional[int] = None):
    where, params = order_filters(start, end, category_id)
    return run_query(f"""
        SELECT DATE_FORMAT(o.order_date, '%%Y-%%m') AS month,
               SUM(oi.quantity * oi.unit_price) AS revenue,
               COUNT(DISTINCT o.id) AS orders
        {BASE} WHERE {where}
        GROUP BY month ORDER BY month
    """, params)


@app.get("/api/top-products")
def top_products(start: Optional[str] = None, end: Optional[str] = None,
                 category_id: Optional[int] = None):
    where, params = order_filters(start, end, category_id)
    return run_query(f"""
        SELECT p.name, SUM(oi.quantity) AS units,
               SUM(oi.quantity * oi.unit_price) AS revenue
        {BASE} WHERE {where}
        GROUP BY p.id, p.name ORDER BY revenue DESC LIMIT 8
    """, params)


@app.get("/api/low-stock")
def low_stock(category_id: Optional[int] = None):
    return run_query("""
        SELECT s.sku, s.name, s.stock, s.reorder_level
        FROM v_current_stock s
        JOIN products p ON p.id = s.product_id
        WHERE (%s IS NULL OR p.category_id = %s)
        ORDER BY s.stock ASC LIMIT 8
    """, [category_id, category_id])