_list:
    just -l --unsorted

[group('run')]
runserver:
    uv run python manage.py runserver

[group('run')]
shell_plus:
    uv run python manage.py shell_plus

[group('deploy')]
deploy: check
    bin/deploy

[group('check')]
check:
    bin/check

[group('check')]
lint:
    bin/checks/lint

[group('check')]
format:
    bin/checks/format

[group('check')]
types:
    bin/checks/types

[group('check')]
test:
    bin/checks/test


[group('migrations')]
showmigrations:
    uv run python manage.py showmigrations

[group('migrations')]
makemigrations:
    uv run python manage.py makemigrations

[group('migrations')]
migrate:
    uv run python manage.py migrate

[group('setup')]
update_packages:
    bin/update_packages

[group('setup')]
initialize_db:
    bin/initialize-db

[group('setup')]
initialize_env:
    bin/initialize_env
