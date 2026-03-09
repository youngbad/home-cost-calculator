# Home Renovation Cost Tracker

A clean, production-like MVP web application for tracking home renovation expenses.  
Built with **Python + Flask**, **SQLAlchemy**, **SQLite** (swappable to PostgreSQL), and a vanilla JS / Chart.js frontend.

---

## Features

| Feature | Details |
|---|---|
| Add / Edit / Delete expenses | name, category, amount, date, optional notes |
| Tagging system | comma-separated tags per expense (kitchen, bathroom, garden…) |
| Filter & sort | by category, tag, date range, and amount |
| Dashboard | total cost, category doughnut chart, monthly bar chart, recent expenses |
| CSV export | download filtered or all expenses as a `.csv` file |
| REST JSON API | full CRUD at `/expenses/api` and `/tags/api` |
| Responsive UI | mobile-first layout, no framework dependencies |

---

## Project Structure

```
home-cost-calculator/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Config classes (dev / prod)
│   ├── models/
│   │   └── __init__.py      # Expense, Tag, expense_tags
│   ├── routes/
│   │   ├── dashboard.py     # Dashboard view
│   │   ├── expenses.py      # Expense HTML views + JSON API
│   │   └── tags.py          # Tags JSON API
│   ├── services/
│   │   └── __init__.py      # Business logic, aggregations, CSV export
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── expenses/
│   │       ├── list.html
│   │       └── form.html
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── migrations/              # Flask-Migrate managed
├── tests.py                 # pytest test suite (18 tests)
├── run.py                   # Entry point
├── requirements.txt
└── .env.example
```

---

## Local Setup

### 1. Clone & create a virtual environment

```bash
git clone <repo-url>
cd home-cost-calculator
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env — at minimum set a SECRET_KEY
```

**SQLite (default – works out of the box):**
```
DATABASE_URL=sqlite:///home_renovation.db
```

**PostgreSQL (for production):**
```
DATABASE_URL=postgresql://user:password@localhost:5432/home_renovation
```

### 4. Initialize the database

```bash
flask db init      # only first time (creates migrations/ folder)
flask db migrate -m "initial"
flask db upgrade
```

### 5. Run the development server

```bash
flask run
# or
python run.py
```

Open [http://localhost:5000](http://localhost:5000).

---

## Running Tests

```bash
pip install pytest
pytest tests.py -v
```

---

## REST API Reference

### Expenses

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/expenses/api` | List all (supports `?category=`, `?tag=`, `?date_from=`, `?date_to=`, `?sort=`) |
| POST | `/expenses/api` | Create expense (JSON body) |
| GET | `/expenses/api/<id>` | Get single expense |
| PUT | `/expenses/api/<id>` | Update expense |
| DELETE | `/expenses/api/<id>` | Delete expense |
| GET | `/expenses/export/csv` | Download CSV |

**Example request body:**
```json
{
  "name": "Kitchen tiles",
  "category": "materials",
  "amount": 450.00,
  "date": "2024-03-10",
  "notes": "Floor tiles for kitchen",
  "tags": ["kitchen", "flooring"]
}
```

### Tags

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/tags/api` | List all tags |
| POST | `/tags/api` | Create tag `{"name": "garden"}` |
| DELETE | `/tags/api/<id>` | Delete tag |

---

## Deployment

### Render (recommended free tier)

1. Push this repo to GitHub.
2. Create a new **Web Service** on [render.com](https://render.com).
3. Set:
   - **Build Command:** `pip install -r requirements.txt && flask db upgrade`
   - **Start Command:** `gunicorn run:app`
4. Add environment variables in the Render dashboard:
   - `SECRET_KEY` — a long random string
   - `DATABASE_URL` — your PostgreSQL URL (Render provides a free PostgreSQL instance)
   - `FLASK_ENV=production`

### Railway / Fly.io

Similar approach — set the same environment variables and use `gunicorn run:app` as the start command.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key` | Flask session secret (change in production!) |
| `DATABASE_URL` | `sqlite:///home_renovation.db` | Database connection string |
| `FLASK_ENV` | `development` | `development` or `production` |
