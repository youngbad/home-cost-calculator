#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Ensuring all database tables are created..."
python -c "from app import create_app, db; app=create_app(); app.app_context().push(); db.create_all()"

echo "Running migrations..."
flask db upgrade
