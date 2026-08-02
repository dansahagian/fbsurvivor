SERVER := "oyuki"
DB_SERVER := "ran"


_list:
    just --list --unsorted

# Run all checks: lint, format, types, test, audit
[group('check')]
check: audit lint format types test

# Audit dependencies
[group('check')]
audit:
    scripts/checks/audit

# Lint with ruff (autofix)
[group('check')]
lint:
    scripts/checks/lint

# Format with ruff
[group('check')]
format:
    scripts/checks/format

# Type-check with ty
[group('check')]
types:
    scripts/checks/types

# Run the test suite
[group('check')]
test:
    scripts/checks/test


# Upgrade locked dependencies
[group('setup')]
upgrade:
    scripts/upgrade

# Create the virtualenv and install deps + pre-commit hooks
[group('setup')]
init-env:
    scripts/init_env

# Restore the local db from a fresh dump of {{DB_SERVER}}
[group('setup')]
init-db:
    ssh {{DB_SERVER}} "pg_dump -U fbsurvivor2 fbsurvivor2 > /tmp/fbsurvivor_dump"
    scp {{DB_SERVER}}:/tmp/fbsurvivor_dump tmp/fbsurvivor_dump
    ssh {{DB_SERVER}} "rm /tmp/fbsurvivor_dump"
    psql -U postgres -d fbsurvivor2 -c "DROP SCHEMA IF EXISTS public CASCADE;"
    psql -U postgres -d postgres -c "DROP DATABASE fbsurvivor2;"
    psql -U postgres -d postgres -c "DROP ROLE fbsurvivor2;"
    psql -U postgres -d postgres -c "CREATE DATABASE fbsurvivor2;"
    psql -U postgres -d postgres -c "CREATE ROLE fbsurvivor2 WITH PASSWORD 'password';"
    psql -U postgres -d postgres -c "ALTER ROLE fbsurvivor2 WITH CREATEDB LOGIN;"
    psql -U postgres -d postgres -c "GRANT ALL ON DATABASE fbsurvivor2 to fbsurvivor2;"
    psql -U postgres -d fbsurvivor2 -c "DROP SCHEMA IF EXISTS public;"
    psql -U postgres -d fbsurvivor2 -c "CREATE SCHEMA IF NOT EXISTS public AUTHORIZATION fbsurvivor2;"
    psql -U postgres fbsurvivor2 < ~/d/code/fbsurvivor/tmp/fbsurvivor_dump

# Print a fresh Django secret key
[group('setup')]
gen-secret-key:
    uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())';
