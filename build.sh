#!/usr/bin/env bash
# exit on error
set -o errexit

# Install all the Python packages from requirements.txt
pip install -r requirements.txt

# Collect all static files (CSS, JS, etc.) into the STATIC_ROOT directory
python manage.py collectstatic --no-input

# Run database migrations to ensure the database is up to date
python manage.py migrate