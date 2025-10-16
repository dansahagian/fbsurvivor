from typing import Dict, Tuple

from django.shortcuts import get_object_or_404

from fbsurvivor.core.models import Board, Pick, Player, PlayerStatus, Season
from fbsurvivor.core.services import PickQuery, PlayerStatusQuery, SeasonService, WeekQuery


def get_player_context(player: Player, year: int) -> Tuple[Season, PlayerStatus | None, dict]:
    season = get_object_or_404(Season, year=year)

    try:
        player_status = PlayerStatus.objects.get(player=player, season=season)
    except PlayerStatus.DoesNotExist:
        player_status = None

    context = {
        "player": player,
        "season": season,
        "player_status": player_status,
    }

    return season, player_status, context


def update_player_records(year: int):
    try:
        season = Season.objects.get(year=year)
    except Season.DoesNotExist:
        return

    for ps in PlayerStatus.objects.filter(season=season):
        update_record(ps)


def update_record(player_status: PlayerStatus) -> bool:
    player = player_status.player
    season = player_status.season

    picks = Pick.objects.filter(player=player, week__season=season)
    player_status.win_count = picks.filter(result="W").count()
    player_status.loss_count = picks.filter(result="L").count()
    player_status.save()
    return True


def get_board(season: Season):
    return (
        Board.objects.filter(season=season)
        .select_related("player_status", "player_status__player")
        .order_by("ranking")
    )


def cache_board(season: Season) -> bool:
    ps = PlayerStatusQuery.for_season_board(season).select_related("player")
    pick_data = [
        (x, list(PickQuery.for_board(x.player, season).select_related("team"))) for x in ps
    ]

    r = 1
    for row in pick_data:
        player_status, picks = row

        defaults: Dict[str, int | str | None] = {"ranking": r}
        for pick in picks:
            defaults[f"pick_{pick.week.week_num:02}"] = pick.team.team_code if pick.team else None
            defaults[f"result_{pick.week.week_num:02}"] = pick.result if pick else None

        Board.objects.update_or_create(
            season=season, player_status=player_status, defaults=defaults
        )
        r += 1

    return True


def cache_current_board() -> bool:
    for season in SeasonService.get_live():
        cache_board(season)
    return True


def cache_boards() -> bool:
    for season in Season.objects.all():
        cache_board(season)
    return True


def can_buy_back(
    player_status: PlayerStatus | None,
    player: Player,
    season: Season,
):
    if not player_status:
        return False

    if player_status.is_survivor:
        return False

    if not player_status.can_buy_back:
        return False

    if not (current_week := WeekQuery.get_current(season)):
        return False

    if player_status.loss_count != 1:
        return False

    if (next_week := WeekQuery.get_next(season)) and next_week.is_locked:
        return False

    try:
        return Pick.objects.get(player=player, week=current_week).result == "L"
    except Pick.DoesNotExist:
        return False
