# Smart Business Management & Analytics System

Sales, inventory and customer analytics with an interactive dashboard and decision-ready reports.

## Tech stack
React (Vite) · FastAPI (Python) · MySQL · Power BI (optional report layer)

## Features (planned)
- [ ] Auth with roles (admin / manager / staff)
- [ ] Products, inventory, customers, orders
- [ ] Revenue trends, category and region breakdowns
- [ ] Customer segmentation (RFM) and lifetime value
- [ ] Sales forecasting
- [ ] Low-stock alerts and reorder suggestions
- [ ] PDF / Excel report export

## Setup
```bash
# 1. Database
mysql -u root -p < database/schema.sql
cp .env.example .env        # then edit the password

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python ../database/seed.py
uvicorn app.main:app --reload

# 3. Frontend (added in the next step)
cd ../frontend && npm install && npm run dev
```

## Project structure
```
frontend/   React dashboard
backend/    FastAPI app and analytics
database/   schema.sql, seed.py
docs/       screenshots, architecture diagram
```
