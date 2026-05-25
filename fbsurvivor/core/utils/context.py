from typing import Tuple

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from fbsurvivor.core.models import Player, PlayerStatus, Season


def get_context(user: User, year: int) -> Tuple[Player, Season, PlayerStatus, dict]:
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)
    player_status = get_object_or_404(PlayerStatus, player=player, season=season)

    context = {
        "player": player,
        "season": season,
        "player_status": player_status,
    }

    return player, season, player_status, context


def get_season_context(year: int, **kwargs) -> Tuple[Season, dict]:
    season = get_object_or_404(Season, year=year)
    return season, {
        "season": season,
        "player": kwargs["player"],
    }
