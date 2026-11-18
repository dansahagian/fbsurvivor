GROUPS   := "check django database setup prod"

_list:
    @echo "Available recipes:"
    @first=1; for g in {{GROUPS}}; do [ $first = 1 ] || echo; first=0; just --list --unsorted --group "$g" --list-heading ""; done

PROJECT       := "fbsurvivor"
DB_USER       := "fbsurvivor2"
DB_NAME       := "fbsurvivor2"
DOMAIN        := "fbsurvivor.com"
SERVER        := "oyuki"

SETTINGS      := PROJECT + ".settings"
PROD_DIR      := SERVER + ":/opt/" + PROJECT
LOCAL_DB_FILE := "tmp/database_file"


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
runserver: (manage "runserver")

[group('django')]
shell_plus: (manage "shell_plus")

[group('django')]
showmigrations: (manage "showmigrations")

[group('django')]
makemigrations: (manage "makemigrations")

[group('django')]
migrate: (manage "migrate") (manage "createcachetable")


# DATABASE

# Initialize your local db
[group('database')]
init-db:
    psql -d postgres -c "DROP DATABASE IF EXISTS {{DB_NAME}};"
    psql -d postgres -c "DROP ROLE IF EXISTS {{DB_USER}};"
    psql -d postgres -c "CREATE DATABASE {{DB_NAME}};"
    psql -d postgres -c "CREATE ROLE {{DB_USER}} WITH PASSWORD 'password';"
    psql -d postgres -c "ALTER ROLE {{DB_USER}} WITH CREATEDB LOGIN;"
    psql -d postgres -c "GRANT ALL ON DATABASE {{DB_NAME}} TO {{DB_USER}};"
    psql -d {{DB_NAME}} -c "DROP SCHEMA IF EXISTS public;"
    psql -d {{DB_NAME}} -c "CREATE SCHEMA public AUTHORIZATION {{DB_USER}};"


# Copy the production db down to the dev host
[group('database')]
copy-db:
    #!/usr/bin/env bash
    set -euo pipefail
    umask 077

    SOCK="$HOME/.ssh/deploy-%r@%h:%p"

    # Prompts for your key passphrase once, then backgrounds
    ssh -fNM -S "$SOCK" "{{SERVER}}"
    trap 'ssh -S "$SOCK" -O exit "{{SERVER}}" 2>/dev/null' EXIT

    # -w: never prompt; the password comes from ~/.pgpass on the server
    ssh -S "$SOCK" "{{SERVER}}" "pg_dump -w -U {{DB_USER}} {{DB_NAME}}" > "{{LOCAL_DB_FILE}}"

# Load the dev database from LOCAL_DB_FILE
[group('database')]
load-db:
    #!/usr/bin/env bash
    set -euo pipefail

    [ -s "{{LOCAL_DB_FILE}}" ] || { echo "❌ file missing or empty" >&2; exit 1; }

    psql -d postgres -c "DROP DATABASE IF EXISTS {{DB_NAME}};"
    psql -d postgres -c "DROP ROLE IF EXISTS {{DB_USER}};"
    psql -d postgres -c "CREATE DATABASE {{DB_NAME}};"
    psql -d postgres -c "CREATE ROLE {{DB_USER}} WITH PASSWORD 'password';"
    psql -d postgres -c "ALTER ROLE {{DB_USER}} WITH CREATEDB LOGIN;"
    psql -d postgres -c "GRANT ALL ON DATABASE {{DB_NAME}} TO {{DB_USER}};"
    psql -d {{DB_NAME}} -c "DROP SCHEMA IF EXISTS public;"
    psql -d {{DB_NAME}} -c "CREATE SCHEMA public AUTHORIZATION {{DB_USER}};"
    psql -v ON_ERROR_STOP=1 {{DB_NAME}} < "{{LOCAL_DB_FILE}}"


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
    set -euo pipefail

    echo "Deploying..."
    SOCK="$HOME/.ssh/deploy-%r@%h:%p"

    # Prompts for your key passphrase once, then backgrounds
    ssh -fNM -S "$SOCK" "{{SERVER}}"
    trap 'ssh -S "$SOCK" -O exit "{{SERVER}}" 2>/dev/null' EXIT

    RSH="ssh -S $SOCK"

    # --no-group: don't copy the Mac's `staff` group; infra/deploy fixes perms on the server
    rsync -a --no-group -e "$RSH" \
      "./{{PROJECT}}" ./pyproject.toml ./uv.lock ./manage.py ./infra/deploy ./uploads \
      "{{PROD_DIR}}"

    ssh -S "$SOCK" "{{SERVER}}" "/opt/{{PROJECT}}/deploy"

    curl -X GET -I "https://{{DOMAIN}}"
