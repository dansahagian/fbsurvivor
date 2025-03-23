from typing import Dict, Tuple

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from fbsurvivor.core.models import Board, Pick, Player, PlayerStatus, Season
from fbsurvivor.core.services import PickQuery, PlayerStatusQuery, SeasonService


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


def send_to_latest_season_played(request, player: Player):
    ps = PlayerStatus.objects.filter(player=player).order_by("-season__year")
    if ps:
        latest = ps[0].season.year  # type: ignore
        messages.info(request, f"No record for the requested year. Here is {latest}")
        return redirect(reverse("board", args=[latest]))
    else:
        messages.info(request, "We don't have a record of you playing any season.")
        return redirect(reverse("login"))


def get_add_on_season(player: Player, season: Season):
    year = season.year * 10 + 1

    try:
        add_on_season = Season.objects.get(year=year)
    except Season.DoesNotExist:
        return None

    try:
        ps_add_on_season = PlayerStatus.objects.get(player=player, season=add_on_season)
    except PlayerStatus.DoesNotExist:
        ps_add_on_season = None

    if (add_on_season.is_locked and ps_add_on_season) or not add_on_season.is_locked:
        return add_on_season

    return None


def update_player_records(year: int) -> int:
    try:
        season = Season.objects.get(year=year)
        player_statuses = PlayerStatus.objects.filter(season=season)
        updates = [update_record(ps) for ps in player_statuses]  # type: ignore
        return len(updates)
    except Season.DoesNotExist:
        return 0


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
    for season in Season.objects.all():  # type: ignore
        cache_board(season)
    return True
