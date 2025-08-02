_list:
    just -l

deploy:
    bin/deploy


[group('check')]
pyright:
    dev/checks/pyright

[group('check')]
ruff:
    dev/checks/ruff-check

[group('check')]
ruff-format:
    dev/checks/ruff-format

[group('check')]
ruff-imports:
    dev/checks/ruff-imports

[group('dev')]
format:
    ruff check --select I --fix
    ruff format

[group('dev')]
initialize_db:
    dev/initialize-db

[group('dev')]
initialize_env:
    rm -rf .venv
    uv venv
    uv sync
    pre-commit install

[group('dev')]
update_packages:
    uv lock --upgrade
    uv sync

[group('manage')]
runserver:
    uv run python manage.py runserver

[group('manage')]
shell_plus:
    uv run python manage.py shell_plus
