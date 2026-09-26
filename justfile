GROUPS   := "check django database setup prod"

_list:
    @echo "Available recipes:"
    @first=1; for g in {{GROUPS}}; do [ $first = 1 ] || echo; first=0; just --list --unsorted --group "$g" --list-heading ""; done

SERVER   := "oyuki"
DOMAIN   := "fbsurvivor.com"

PROJECT  := "fbsurvivor"
SETTINGS := PROJECT + ".settings"
PORT     := "8000"

DB_NAME  := "fbsurvivor2"
DB_USER  := "fbsurvivor2"
DB_PASS  := "password"
DB_DUMP  := "tmp/fbsurvivor_dump"

SERVICE   := "wsgi-server-" + PROJECT + ".service"
PROD_UV   := "/home/dan/.cargo/bin/uv"


# CHECK

[group('check')]
check: audit lint format types test

[group('check')]
audit:
    uv audit --preview-features audit

[group('check')]
lint:
    uv run ruff check --fix

[group('check')]
format:
    uv run ruff format

[group('check')]
types:
    uv run ty check

[group('check')]
test *ARGS:
    uv run pytest {{ if ARGS == "" { "." } else { ARGS } }}


# DJANGO

[group('django')]
manage *ARGS:
    DJANGO_SETTINGS_MODULE={{SETTINGS}} uv run python manage.py {{ARGS}}

[group('django')]
runserver: (manage "runserver 127.0.0.1:" + PORT)

[group('django')]
shell_plus: (manage "shell_plus")

[group('django')]
showmigrations: (manage "showmigrations")

[group('django')]
makemigrations: (manage "makemigrations")

[group('django')]
migrate: (manage "migrate")


# DATABASE

# Initialize your local db
[group('database')]
init-db:
    psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS {{DB_NAME}};"
    psql -U postgres -d postgres -c "DROP ROLE IF EXISTS {{DB_USER}};"
    psql -U postgres -d postgres -c "CREATE DATABASE {{DB_NAME}};"
    psql -U postgres -d postgres -c "CREATE ROLE {{DB_USER}} WITH PASSWORD '{{DB_PASS}}';"
    psql -U postgres -d postgres -c "ALTER ROLE {{DB_USER}} WITH CREATEDB LOGIN;"
    psql -U postgres -d postgres -c "GRANT ALL ON DATABASE {{DB_NAME}} TO {{DB_USER}};"

# Copy the production db down to the dev host
[group('database')]
copy-db:
    ssh {{SERVER}} "pg_dump -U fbsurvivor2 fbsurvivor2 > /tmp/fbsurvivor_dump"
    scp {{SERVER}}:/tmp/fbsurvivor_dump tmp/fbsurvivor_dump
    ssh {{SERVER}} "rm /tmp/fbsurvivor_dump"

# Load the dev database from DB_DUMP
[group('database')]
load-db:
    #!/usr/bin/env bash
    set -euo pipefail
    [ -s "{{DB_DUMP}}" ] || { echo "❌ {{DB_DUMP}} missing or empty" >&2; exit 1; }
    psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS {{DB_NAME}};"
    psql -U postgres -d postgres -c "DROP ROLE IF EXISTS {{DB_USER}};"
    psql -U postgres -d postgres -c "CREATE DATABASE {{DB_NAME}};"
    psql -U postgres -d postgres -c "CREATE ROLE {{DB_USER}} WITH PASSWORD '{{DB_PASS}}';"
    psql -U postgres -d postgres -c "ALTER ROLE {{DB_USER}} WITH CREATEDB LOGIN;"
    psql -U postgres -d postgres -c "GRANT ALL ON DATABASE {{DB_NAME}} TO {{DB_USER}};"
    psql -U postgres -d {{DB_NAME}} -c "DROP SCHEMA IF EXISTS public;"
    psql -U postgres -d {{DB_NAME}} -c "CREATE SCHEMA public AUTHORIZATION {{DB_USER}};"
    psql -U postgres -v ON_ERROR_STOP=1 {{DB_NAME}} < "{{DB_DUMP}}"


# SETUP

# Recreate the virtualenv, install deps + pre-commit hooks
[group('setup')]
init-env:
    rm -rf .venv
    uv venv
    uv sync
    uv run pre-commit install

# Upgrade locked dependencies
[group('setup')]
upgrade:
    uv lock --upgrade
    uv sync


# Deploy in production
[group('prod')]
deploy: check
    #!/usr/bin/env bash
    SERVER="oyuki"

    set -e

    echo "Deploying..."

    rsync -a ./fbsurvivor $SERVER:/opt/fbsurvivor
    rsync -a ./pyproject.toml $SERVER:/opt/fbsurvivor
    rsync -a ./uv.lock $SERVER:/opt/fbsurvivor
    rsync -a ./manage.py $SERVER:/opt/fbsurvivor
    rsync -a ./infra/deploy $SERVER:/opt/fbsurvivor
    rsync -a ./uploads $SERVER:/opt/fbsurvivor

    ssh $SERVER /opt/fbsurvivor/deploy

    curl -X GET -I https://fbsurvivor.com
