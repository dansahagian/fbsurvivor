# python.just — shared tooling for uv + ruff + ty + pytest projects.
# Base layer: nothing here is Django-specific.
# Vendored. Edit upstream, then `just sync-tooling`.
#
# These let any importing justfile override the variables and recipes below.
# They must live here, at the base of the import chain, and must NOT be
# repeated downstream — settings cannot be duplicated across an import.
set allow-duplicate-variables
set allow-duplicate-recipes

PROJECT   := file_stem(justfile_directory())
UV        := "uv"
DEV_HOST  := "onryo"
PROD_HOST := "oyuki"
PYTHON_JUST := env("PYTHON_JUST_URL", "https://raw.githubusercontent.com/dan/just-python/main/python.just")

# fail unless running on HOST
_on HOST:
    @[ "$(hostname -s)" = "{{HOST}}" ] || { echo "❌ Failed: Not {{HOST}}"; exit 1; }

# Run all checks: audit, lint, format, types, test
[group('check')]
check: audit lint format types test

[group('check')]
audit:
    {{UV}} audit --preview-features audit

[group('check')]
lint:
    {{UV}} run ruff check --fix

[group('check')]
format:
    {{UV}} run ruff format

[group('check')]
types:
    {{UV}} run ty check

[group('check')]
test *ARGS:
    {{UV}} run pytest {{ if ARGS == "" { "." } else { ARGS } }}

# Recreate the virtualenv, install deps + pre-commit hooks
[group('dev')]
init-env: (_on DEV_HOST)
    rm -rf .venv
    {{UV}} venv
    {{UV}} sync
    {{UV}} run pre-commit install

# Upgrade locked dependencies
[group('dev')]
upgrade: (_on DEV_HOST)
    {{UV}} lock --upgrade
    {{UV}} sync

# Pull the latest shared tooling for python
[group('tooling')]
sync-python: (_on DEV_HOST)
    curl -fsSL {{PYTHON_JUST}} -o {{justfile_directory()}}/just-python.just
    @git -C {{justfile_directory()}} diff --stat -- just-python.just
