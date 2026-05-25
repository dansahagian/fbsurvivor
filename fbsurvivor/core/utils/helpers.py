from typing import Dict

from django.shortcuts import redirect, render
from django.urls import reverse

from fbsurvivor.core.models import Board, Pick, Player, PlayerStatus, Season
from fbsurvivor.core.queries import (
    get_current_week,
    get_live_seasons,
    get_next_week,
    get_player_statuses_for_season_board,
    picks_for_board,
)
from fbsurvivor.settings import CONTACT


def get_player_status(player: Player, season: Season) -> PlayerStatus | None:
    try:
        return PlayerStatus.objects.get(player=player, season=season)
    except PlayerStatus.DoesNotExist:
        return None


def send_to_latest_season_played(request, player: Player):
    ps = PlayerStatus.objects.filter(player=player).order_by("-season__year")
    if ps:
        context = {"player": player, "latest": ps[0].season.year, "contact": CONTACT}
        return render(request, "error-board.html", context=context)
    else:
        return redirect(reverse("index"))


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
        .select_related("player_status", "player_status__player", "player_status__player__user")
        .order_by("ranking")
    )


def cache_board(season: Season) -> bool:
    ps = get_player_statuses_for_season_board(season)
    pick_data = [(x, list(picks_for_board(x.player, season).select_related("team"))) for x in ps]

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
    for season in get_live_seasons():
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

    if not (current_week := get_current_week(season)):
        return False

    if player_status.loss_count != 1:
        return False

    if (next_week := get_next_week(season)) and next_week.is_locked:
        return False

    try:
        return Pick.objects.get(player=player, week=current_week).result == "L"
    except Pick.DoesNotExist:
        return False
