Logbook Trip Planner

Full-stack app for planning trips and viewing ELD log sheets.

Stack: Django + DRF, PostgreSQL, React (Vite)

- Features

- Trip Planner (address search, route polyline, HOS-compliant daily logs)
- Logs Viewer (scroll through generated log sheet images)

API

- POST /api/plan-trip/
- GET /api/places-search/?q=
- GET /api/trip-logs/
- GET /api/trip-logs/<id>/

Run Locally

- Backend

cd backend
python -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver

- Frontend

cd frontend
npm install
npm run dev
