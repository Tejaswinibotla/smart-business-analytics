import os
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


@app.get("/health")
def health():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS orders FROM orders")
            return {"status": "ok", **cur.fetchone()}
    finally:
        conn.close()


@app.get("/api/kpis")
def kpis():
    """First analytics endpoint: headline numbers for the dashboard."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(total_amount),0) AS revenue,
                       COUNT(*) AS orders,
                       COALESCE(AVG(total_amount),0) AS avg_order_value
                FROM orders WHERE status = 'completed'
                  AND order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            return cur.fetchone()
    finally:
        conn.close()
