_list:
    just -l --unsorted

[group('run')]
runserver:
    uv run python manage.py runserver

[group('run')]
shell_plus:
    uv run python manage.py shell_plus

[group('deploy')]
deploy:
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

[group('dev')]
update_packages:
    bin/dev/update_packages

[group('dev')]
initialize_db:
    bin/dev/initialize-db

[group('dev')]
initialize_env:
    bin/dev/initialize_env
