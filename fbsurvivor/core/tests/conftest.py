from datetime import timedelta

import pytest
from django.utils import timezone
from factory.declarations import Iterator

from fbsurvivor.core.tests.factories import (
    PickFactory,
    PlayerFactory,
    PlayerStatusFactory,
    SeasonFactory,
    TeamFactory,
    WeekFactory,
)


@pytest.fixture(autouse=True)
def players(db):
    return PlayerFactory.create_batch(
        size=2,
        username=Iterator(["Automator", "Roboto"]),
    )


@pytest.fixture(autouse=True)
def seasons(db):
    return SeasonFactory.create_batch(
        size=2,
        year=Iterator([2019, 2020]),
        is_locked=Iterator([True, False]),
        is_current=Iterator([False, True]),
    )


@pytest.fixture(autouse=True)
def weeks(db, seasons):
    right_now = timezone.now()
    nw = right_now + timedelta(days=7)
    lw = right_now + timedelta(days=-7)
    ly = right_now + timedelta(days=-365)

    return {
        "this_season": WeekFactory.create_batch(
            size=5,
            season=seasons[1],
            week_num=Iterator([1, 2, 3, 4, 5]),
            lock_datetime=Iterator([lw, lw, lw, lw, nw]),
        ),
        "last_season": WeekFactory.create_batch(
            size=5,
            season=seasons[0],
            week_num=Iterator([1, 2, 3, 4, 5]),
            lock_datetime=ly,
        ),
    }


@pytest.fixture(autouse=True)
def teams(db, seasons):
    return {
        "this_season": TeamFactory.create_batch(
            size=6,
            season=seasons[1],
            team_code=Iterator(["NE", "SF", "TB", "GB", "DAL", "BUF"]),
            bye_week=Iterator([1, 1, 2, 2, 3]),
        ),
        "last_season": TeamFactory.create_batch(
            size=5,
            season=seasons[0],
            team_code=Iterator(["NE", "SF", "TB", "GB", "DAL"]),
            bye_week=Iterator([1, 1, 2, 2, 3]),
        ),
    }


@pytest.fixture(autouse=True)
def picks(db, players, weeks, teams):
    seasons = ["this_season", "last_season"]
    return {
        "p1": {x: _picks(players[0], weeks[x], teams[x]) for x in seasons},
        "p2": {x: _picks(players[1], weeks[x], reversed(teams[x])) for x in seasons},
    }


@pytest.fixture(autouse=True)
def player_statuses(db, players, seasons):
    return {
        "p1": PlayerStatusFactory.create_batch(
            size=2, player=players[0], season=Iterator(seasons)
        ),
        "p2": PlayerStatusFactory.create_batch(
            size=2, player=players[1], season=Iterator(seasons)
        ),
    }


def _picks(player, weeks, teams):
    return PickFactory.create_batch(
        size=5,
        player=player,
        week=Iterator(weeks),
        team=Iterator(teams),
    )
