DB_FILE := "/tmp/fbsurvivor_dump"

_list:
    just --list --unsorted


# Run the Django development server
[group('django')]
runserver:
    DJANGO_SETTINGS_MODULE=fbsurvivor.settings uv run python manage.py runserver 0.0.0.0:8000

# Run the Django shell
[group('django')]
shell_plus:
    DJANGO_SETTINGS_MODULE=fbsurvivor.settings uv run python manage.py shell_plus

# Show all migrations
[group('django')]
showmigrations:
    DJANGO_SETTINGS_MODULE=fbsurvivor.settings uv run python manage.py showmigrations

# Make migrations
[group('django')]
makemigrations:
    DJANGO_SETTINGS_MODULE=fbsurvivor.settings uv run python manage.py makemigrations

# Migrate the database
[group('django')]
migrate:
    DJANGO_SETTINGS_MODULE=fbsurvivor.settings uv run python manage.py migrate


# Print a fresh Django secret key
[group('django')]
gen-secret-key:
    uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())';


# Run all checks: lint, format, types, test, audit
[group('check')]
check: audit lint format types test

# Audit dependencies
[group('check')]
audit:
    bin/checks/audit

# Lint with ruff (autofix)
[group('check')]
lint:
    bin/checks/lint

# Format with ruff
[group('check')]
format:
    bin/checks/format

# Type-check with ty
[group('check')]
types:
    bin/checks/types

# Run the test suite
[group('check')]
test:
    bin/checks/test


# Create the virtualenv and install deps + pre-commit hooks
[group('dev')]
init-env:
    bin/dev/init-env

# Load the db from /tmp/fbsurvivor_dump
[group('dev')]
load-db:
    bin/dev/load-db

# Upgrade locked dependencies
[group('dev')]
upgrade:
    bin/dev/upgrade


# Copy production db to development
[group('prod')]
copy-db:
    bin/prod/copy-db

# Deploy in production
deploy:
    bin/prod/deploy
