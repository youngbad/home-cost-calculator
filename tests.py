"""Basic integration tests for the Home Renovation Cost Tracker."""
import pytest
from datetime import date

from app import create_app, db
from app.models import Expense, Tag


@pytest.fixture
def app():
    app = create_app("default")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_data(app):
    with app.app_context():
        tag = Tag(name="kitchen")
        db.session.add(tag)
        e1 = Expense(name="Tiles", category="materials", amount=500.0, date=date(2024, 3, 1))
        e1.tags = [tag]
        e2 = Expense(name="Plumber", category="labor", amount=200.0, date=date(2024, 4, 5))
        db.session.add_all([e1, e2])
        db.session.commit()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def test_dashboard_loads(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_dashboard_shows_total(client, sample_data):
    resp = client.get("/")
    assert b"700.00" in resp.data


# ---------------------------------------------------------------------------
# Expenses list
# ---------------------------------------------------------------------------

def test_expenses_list(client, sample_data):
    resp = client.get("/expenses/")
    assert resp.status_code == 200
    assert b"Tiles" in resp.data
    assert b"Plumber" in resp.data


def test_expenses_filter_by_category(client, sample_data):
    resp = client.get("/expenses/?category=labor")
    assert b"Plumber" in resp.data
    assert b"Tiles" not in resp.data


def test_expenses_filter_by_tag(client, sample_data):
    resp = client.get("/expenses/?tag=kitchen")
    assert b"Tiles" in resp.data
    assert b"Plumber" not in resp.data


# ---------------------------------------------------------------------------
# Add expense
# ---------------------------------------------------------------------------

def test_add_expense_get(client):
    resp = client.get("/expenses/add")
    assert resp.status_code == 200


def test_add_expense_post(client):
    resp = client.post(
        "/expenses/add",
        data={
            "name": "New Sink",
            "category": "materials",
            "amount": "150.00",
            "date": "2024-05-10",
            "notes": "For bathroom",
            "tags": "bathroom",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"New Sink" in resp.data


def test_add_expense_validation_empty(client):
    resp = client.post(
        "/expenses/add",
        data={"name": "", "category": "", "amount": "", "date": ""},
        follow_redirects=True,
    )
    assert b"required" in resp.data.lower() or b"danger" in resp.data.lower()


# ---------------------------------------------------------------------------
# Edit & Delete
# ---------------------------------------------------------------------------

def test_edit_expense(client, sample_data):
    with client.application.app_context():
        e = Expense.query.first()
        eid = e.id

    resp = client.post(
        f"/expenses/{eid}/edit",
        data={"name": "Updated Tiles", "category": "materials", "amount": "600.00", "date": "2024-03-01"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Updated Tiles" in resp.data


def test_delete_expense(client, sample_data):
    with client.application.app_context():
        e = Expense.query.filter_by(name="Tiles").first()
        eid = e.id

    resp = client.post(f"/expenses/{eid}/delete", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Tiles" not in resp.data


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def test_csv_export(client, sample_data):
    resp = client.get("/expenses/export/csv")
    assert resp.status_code == 200
    assert resp.content_type.startswith("text/csv")
    data = resp.data.decode()
    assert "Tiles" in data
    assert "Plumber" in data


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

def test_api_list(client, sample_data):
    resp = client.get("/expenses/api")
    assert resp.status_code == 200
    items = resp.get_json()
    assert isinstance(items, list)
    assert len(items) == 2


def test_api_create(client):
    resp = client.post(
        "/expenses/api",
        json={"name": "Paint", "category": "materials", "amount": 80.0, "date": "2024-06-01"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "Paint"


def test_api_update(client, sample_data):
    with client.application.app_context():
        e = Expense.query.first()
        eid = e.id

    resp = client.put(
        f"/expenses/api/{eid}",
        json={"name": "Renamed", "category": "materials", "amount": 100.0, "date": "2024-03-01"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Renamed"


def test_api_delete(client, sample_data):
    with client.application.app_context():
        e = Expense.query.first()
        eid = e.id

    resp = client.delete(f"/expenses/api/{eid}")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Tags API
# ---------------------------------------------------------------------------

def test_tags_api_list(client, sample_data):
    resp = client.get("/tags/api")
    assert resp.status_code == 200
    tags = resp.get_json()
    assert any(t["name"] == "kitchen" for t in tags)


def test_tags_api_create(client):
    resp = client.post("/tags/api", json={"name": "Garden"})
    assert resp.status_code == 201
    assert resp.get_json()["name"] == "garden"


# ---------------------------------------------------------------------------
# Aggregations (services unit tests)
# ---------------------------------------------------------------------------

def test_aggregations(app, sample_data):
    with app.app_context():
        from app.services import get_total_cost, get_cost_by_category, get_monthly_summary
        assert get_total_cost() == 700.0
        by_cat = get_cost_by_category()
        assert by_cat["materials"] == 500.0
        assert by_cat["labor"] == 200.0
        monthly = get_monthly_summary()
        assert len(monthly) == 2
