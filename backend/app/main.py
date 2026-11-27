import json
import os
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
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


# ---------- Customer segmentation (RFM) ----------

SEGMENT_ORDER = ["Champions", "Loyal", "Promising",
                 "Needs attention", "At risk", "Hibernating"]


def rfm_label(r, f, m):
    """r, f, m are scores from 1 (worst) to 5 (best)."""
    fm = (f + m) / 2
    if r >= 4 and fm >= 4:
        return "Champions"        # recent, frequent, high spend
    if r >= 3 and fm >= 3:
        return "Loyal"            # regular, good spend
    if r >= 4:
        return "Promising"        # recent but low spend so far
    if r == 3:
        return "Needs attention"  # average, starting to cool off
    if fm >= 3:
        return "At risk"          # good customers who went quiet
    return "Hibernating"          # low spend and gone quiet


@app.get("/api/customer-segments")
def customer_segments():
    rows = run_query("""
        SELECT c.id, c.name, c.city,
               DATEDIFF(CURDATE(), MAX(o.order_date)) AS recency,
               COUNT(DISTINCT o.id) AS frequency,
               SUM(oi.quantity * oi.unit_price) AS monetary
        FROM customers c
        JOIN orders o ON o.customer_id = c.id AND o.status = 'completed'
        JOIN order_items oi ON oi.order_id = o.id
        GROUP BY c.id, c.name, c.city
    """)
    if len(rows) < 5:
        return {"segments": [], "at_risk": []}

    df = pd.DataFrame(rows)
    df["recency"] = df["recency"].astype(int)
    df["frequency"] = df["frequency"].astype(int)
    df["monetary"] = df["monetary"].astype(float)

    # Score each customer 1-5 (rank first so ties never break the bins)
    df["r"] = pd.qcut(df["recency"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    df["f"] = pd.qcut(df["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["m"] = pd.qcut(df["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["segment"] = [rfm_label(r, f, m) for r, f, m in zip(df["r"], df["f"], df["m"])]

    summary = (
        df.groupby("segment")
        .agg(customers=("id", "count"), revenue=("monetary", "sum"),
             avg_recency=("recency", "mean"))
        .reindex(SEGMENT_ORDER)
        .dropna()
        .reset_index()
    )
    summary["customers"] = summary["customers"].astype(int)
    summary["revenue"] = summary["revenue"].round(0)
    summary["avg_recency"] = summary["avg_recency"].round(0)

    at_risk = (
        df[df["segment"] == "At risk"]
        .sort_values("monetary", ascending=False)
        .head(8)[["name", "city", "recency", "frequency", "monetary"]]
    )

    return {
        "segments": json.loads(summary.to_json(orient="records")),
        "at_risk": json.loads(at_risk.to_json(orient="records")),
    }


# ---------- Revenue forecast ----------

@app.get("/api/forecast")
def forecast(category_id: Optional[int] = None, months: int = 3):
    """Fit a straight-line trend to monthly revenue and project it forward."""
    months = max(1, min(months, 6))
    where, params = order_filters(None, None, category_id)
    rows = run_query(f"""
        SELECT DATE_FORMAT(o.order_date, '%%Y-%%m') AS month,
               SUM(oi.quantity * oi.unit_price) AS revenue
        {BASE} WHERE {where}
        GROUP BY month ORDER BY month
    """, params)
    first = run_query("SELECT MIN(order_date) AS d FROM orders")[0]["d"]

    empty = {"history": [], "forecast": [], "trend_per_month": 0, "typical_error_pct": 0}
    if not rows or first is None:
        return empty

    # Only use complete months: skip the current one and a partial first one
    skip = {date.today().strftime("%Y-%m")}
    if first.day > 1:
        skip.add(first.strftime("%Y-%m"))
    history = [{"month": r["month"], "revenue": float(r["revenue"])}
               for r in rows if r["month"] not in skip]
    if len(history) < 4:
        return {**empty, "history": history}

    y = np.array([h["revenue"] for h in history])
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    resid = y - (slope * x + intercept)
    spread = float(np.std(resid, ddof=2))
    error_pct = float(np.mean(np.abs(resid)) / np.mean(y) * 100)

    future = []
    for i in range(1, months + 1):
        value = max(0.0, slope * (len(y) - 1 + i) + intercept)
        future.append({
            "month": str(pd.Period(history[-1]["month"], "M") + i),
            "revenue": round(value),
            "low": round(max(0.0, value - 1.28 * spread)),
            "high": round(value + 1.28 * spread),
        })

    return {
        "history": history,
        "forecast": future,
        "trend_per_month": round(float(slope)),
        "typical_error_pct": round(error_pct, 1),
    }
# ---------- Reorder suggestions ----------

from math import ceil

LEAD_TIME_DAYS = 7   # assumed supplier delivery time
COVER_DAYS = 30      # each order should cover this many days of sales


@app.get("/api/reorder")
def reorder(category_id: Optional[int] = None):
    rows = run_query("""
        SELECT p.sku, p.name, p.cost_price, sup.name AS supplier,
               st.stock, COALESCE(v.units, 0) AS units_30d
        FROM products p
        JOIN v_current_stock st ON st.product_id = p.id
        LEFT JOIN suppliers sup ON sup.id = p.supplier_id
        LEFT JOIN (
            SELECT oi.product_id, SUM(oi.quantity) AS units
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status = 'completed'
              AND o.order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY oi.product_id
        ) v ON v.product_id = p.id
        WHERE p.is_active = TRUE AND (%s IS NULL OR p.category_id = %s)
    """, [category_id, category_id])

    items = []
    for r in rows:
        stock = int(r["stock"])
        daily = float(r["units_30d"]) / 30          # units sold per day
        days_left = stock / daily if daily > 0 else None

        if daily == 0:
            status = "No recent sales"
        elif stock <= 0 or days_left <= LEAD_TIME_DAYS:
            status = "Order now"                    # will run out before a delivery arrives
        elif days_left <= LEAD_TIME_DAYS + 14:
            status = "Order soon"
        else:
            status = "Healthy"

        # Enough to cover the lead time plus COVER_DAYS of sales, minus what we have
        qty = max(0, ceil(daily * (LEAD_TIME_DAYS + COVER_DAYS) - stock))
        if status in ("Healthy", "No recent sales"):
            qty = 0

        items.append({
            "sku": r["sku"],
            "name": r["name"],
            "supplier": r["supplier"],
            "stock": stock,
            "daily_sales": round(daily, 1),
            "days_left": round(days_left, 1) if days_left is not None else None,
            "status": status,
            "suggested_qty": qty,
            "est_cost": round(qty * float(r["cost_price"])),
        })

    # Most urgent first (no recent sales goes to the bottom)
    items.sort(key=lambda i: i["days_left"] if i["days_left"] is not None else 10**9)

    return {
        "lead_time_days": LEAD_TIME_DAYS,
        "cover_days": COVER_DAYS,
        "order_now": sum(1 for i in items if i["status"] == "Order now"),
        "order_soon": sum(1 for i in items if i["status"] == "Order soon"),
        "total_cost": sum(i["est_cost"] for i in items),
        "items": items[:10],
    }