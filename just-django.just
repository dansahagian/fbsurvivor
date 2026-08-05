# just-django.just — shared tooling for Django projects.
# Layers on top of just-python.just, which carries the checks, the dev-env
# recipes, and the duplicate-override settings for the whole chain.
# Vendored. Edit upstream, then `just sync-tooling`.

import 'just-python.just'


SETTINGS  := PROJECT + ".settings"
PORT      := "8000"
DB_NAME   := PROJECT
DB_USER   := PROJECT
DB_PASS   := "password"
DB_DUMP   := "/tmp/" + PROJECT + "_dump"
APP_DIR   := "/opt/" + PROJECT
SERVICE   := "wsgi-server-" + PROJECT + ".service"
DOMAIN    := PROJECT + ".com"
PROD_UV   := "/home/dan/.cargo/bin/uv"
DJANGO_JUST := env("DJANGO_JUST_URL", "https://raw.githubusercontent.com/dan/just-django/main/django.just")

# Run an arbitrary manage.py command
[group('django')]
manage *ARGS:
    DJANGO_SETTINGS_MODULE={{SETTINGS}} {{UV}} run python manage.py {{ARGS}}

[group('django')]
runserver: (manage "runserver 0.0.0.0:" + PORT)

[group('django')]
shell_plus: (manage "shell_plus")

[group('django')]
showmigrations: (manage "showmigrations")

[group('django')]
makemigrations: (manage "makemigrations")

[group('django')]
migrate: (manage "migrate")

# Print a fresh Django secret key
[group('django')]
gen-secret-key:
    @{{UV}} run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Copy the production db down to the dev host
[group('dev')]
copy-db: (_on PROD_HOST)
    pg_dump -U {{DB_USER}} {{DB_NAME}} | ssh "{{DEV_HOST}}" "cat > {{DB_DUMP}}"

# Load the dev database from DB_DUMP
[group('dev')]
load-db: (_on DEV_HOST)
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

# Deploy in production
[group('prod')]
deploy: (_on PROD_HOST)
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{APP_DIR}}
    echo "Deploying..."
    git pull origin main
    {{PROD_UV}} sync --no-dev
    # set -e must not leave the site down if a step below fails
    trap 'sudo systemctl start {{SERVICE}}' EXIT
    sudo systemctl stop {{SERVICE}}
    {{PROD_UV}} run --no-dev python manage.py migrate
    {{PROD_UV}} run --no-dev python manage.py collectstatic --clear --no-input
    {{PROD_UV}} run --no-dev python manage.py check --deploy
    sudo systemctl start {{SERVICE}}
    trap - EXIT
    sleep 2
    curl -X GET -I https://{{DOMAIN}}

# Pull the latest shared tooling for django
[group('tooling')]
sync-django:
    curl -fsSL {{DJANGO_JUST}} -o {{justfile_directory()}}/just-django.just
    @git -C {{justfile_directory()}} diff --stat -- just-django.just
