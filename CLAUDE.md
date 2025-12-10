# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django application for running an NFL Survivor Pool.
It's a ground-up rewrite (version 3.0) that uses Django's ORM.
It replaces previous versions that used Flask with raw SQL queries.

**Stack:**
- Django (Python 3.13+)
- PostgreSQL with psycopg[c]
- uv for package management
- Ruff for linting and formatting
- ty for type checking
- pytest with pytest-django for testing

## Development Commands

All commands use `just` (justfile) or direct `bin/` scripts:

**Running the application:**
```bash
just runserver           # Start development server
just shell_plus          # Django shell with models auto-imported
```

**Quality checks:**
```bash
just check               # Run all checks (lint, format, types, test)
just lint                # Ruff linting with auto-fix
just format              # Ruff formatting
just types               # Type checking with ty
just test                # Run pytest suite
```

**Database migrations:**
```bash
just showmigrations      # Show migration status
just makemigrations      # Create new migrations
just migrate             # Apply migrations
```

**Development setup:**
```bash
just initialize_env      # Set up environment
just initialize_db       # Initialize database
just update_packages     # Update dependencies
```

**Deployment:**
```bash
just deploy              # Deploy to production (runs bin/deploy)
```

**Testing:**
- Run all tests: `uv run pytest .`
- Run specific test: `uv run pytest fbsurvivor/core/tests/test_models.py::TestClassName::test_method_name`

## Architecture

### Core App Structure

The application is a single Django app (`fbsurvivor.core`) with the following organization:

**Key Models (fbsurvivor/core/models.py):**
- `Player`: User accounts with username, email, preferences (dark mode, email reminders)
- `Season`: NFL seasons (year, current/locked/live status)
- `Week`: Weeks within a season with lock times
- `Team`: NFL teams (team_code, bye_week)
- `Lock`: Per-team lock times within a week (for Thursday/Monday games)
- `Pick`: Player's team selection for a week
- `PlayerStatus`: Player's status in a season (paid, retired, survivor status, buy-back eligibility)
- `Board`: Cached leaderboard data for performance
- `MagicLink`: Passwordless authentication links (30-minute expiration)
- `LoggedOutTokens`: JWT token denylist

**Service Layer (fbsurvivor/core/services.py):**
- `PlayerService`: Player creation and account setup
- `SeasonService`: Season queries and next week logic
- `PlayerStatusQuery`: Player status filtering and ordering
- `WeekQuery`: Week filtering (current, next, display)
- `PayoutQuery`: Payout calculations
- `PickQuery`: Pick filtering for various contexts

**Views (fbsurvivor/core/views.py):**
All views are function-based with decorators:
- `@authenticate_player`: Requires valid JWT in session
- `@authenticate_admin`: Requires admin player with valid JWT

**Utils (fbsurvivor/core/utils/):**
- `auth.py`: JWT authentication, magic link generation, decorators
- `emails.py`: Email sending utilities
- `helpers.py`: Board caching, player record updates, buy-back logic
- `deadlines.py`: Lock time calculations
- `reminders.py`: Reminder logic

### Authentication Flow

1. User enters email on login page
2. System creates `MagicLink` and sends email
3. User clicks link → `enter` view validates link, creates JWT, stores in session
4. JWT stored in session, validated by `@authenticate_player` decorator
5. Logout adds token to `LoggedOutTokens` blacklist

### Board Caching

The `Board` model caches leaderboard data to avoid expensive queries:
- Created/updated via `cache_board(season)` in `helpers.py`
- Regenerated when: players pay, picks change results, players buy back
- Admin can manually regenerate via `/cache_season/<year>/`

### Lock Times

Games can have different lock times:
- Default: Week-level `lock_datetime`
- Per-team override: `Lock` model (for Thursday/Monday games)
- Logic in `Team.is_locked()` and `Pick.is_locked` property

### Manager (Admin) Workflow

Admins manage the season through `/manager/<year>/`:
1. Mark players as paid (`/paid/<year>/`)
2. Record game results (`/results/<year>/`) - updates `Pick.result` and `PlayerStatus.is_survivor`
3. View all players (`/players/<year>/`)
4. Results automatically update win/loss counts via `update_player_records()`

## Configuration

**Environment variables (required in .env):**
- `ENV`: "dev" or "prod" (affects DEBUG, ALLOWED_HOSTS, security settings)
- `DOMAIN`: Application domain
- `SECRET_KEY`: Django secret key
- `SMTP_*`: Email configuration (server, sender, user, password, port)
- `PG*`: PostgreSQL connection (database, user, password, host)
- `CONTACT`: Admin contact email
- `VENMO`: Venmo handle for payments

**Settings notes:**
- Dev mode enables django-debug-toolbar and allows all hosts
- Production uses signed cookie sessions (no server-side session storage)
- Timezone: America/Los_Angeles
- HTML minification enabled in production

## Code Patterns

**Query optimization:**
- Use `select_related()` for ForeignKeys
- Use `prefetch_related()` for reverse relations
- Services in `services.py` provide reusable querysets

**URL routing:**
- Year-based URLs: `/board/2024/`, `/picks/2024/`
- All core URLs defined in `fbsurvivor/core/urls.py`

**Management commands:**
- `load_teams`: Import team data for a season
- `load_weeks`: Create week records
- `load_game_locks`: Import per-game lock times
- `send_reminders`: Email players with missing picks
- `cache_current_board`: Regenerate board cache

**Testing:**
- pytest with pytest-django
- Django settings module: `fbsurvivor.settings` (configured in pytest.ini)
- Use factory-boy for test fixtures

## Type Checking

This project uses `ty` for type checking. Key configuration in pyproject.toml:
- django-stubs enabled
- Django settings module: `fbsurvivor.settings`
- Run with `just types` or `uv run ty check`
