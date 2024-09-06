from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from fbsurvivor.core.models import Board, Pick, Player, PlayerStatus, Season


def get_player_context(player: Player, year: int) -> (Season, PlayerStatus, dict):
    season = get_object_or_404(Season, year=year)
    current_season = get_current_season()

    try:
        player_status = PlayerStatus.objects.get(player=player, season=season)
    except PlayerStatus.DoesNotExist:
        player_status = None

    context = {
        "player": player,
        "season": season,
        "player_status": player_status,
        "current_season": current_season,
    }

    return season, player_status, context


def get_current_season() -> Season:
    return Season.objects.get(is_current=True)


def send_to_latest_season_played(request, player: Player):
    ps = PlayerStatus.objects.filter(player=player).order_by("-season__year")
    if ps:
        latest = ps[0].season.year
        messages.info(request, f"No record for the requested year. Here is {latest}")
        return redirect(reverse("board", args=[latest]))
    else:
        messages.info(request, "We don't have a record of you playing any season.")
        return redirect(reverse("login"))


def update_player_records(year: int) -> int:
    try:
        season = Season.objects.get(year=year)
        player_statuses = PlayerStatus.objects.filter(season=season)
        updates = [update_record(ps) for ps in player_statuses]
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
    ps = PlayerStatus.objects.for_season_board(season).select_related("player")
    pick_data = [
        (x, list(Pick.objects.for_board(x.player, season).select_related("team"))) for x in ps
    ]

    r = 1
    for row in pick_data:
        player_status, picks = row

        defaults = {"ranking": r}
        for pick in picks:
            defaults[f"pick_{pick.week.week_num:02}"] = pick.team.team_code if pick.team else None
            defaults[f"result_{pick.week.week_num:02}"] = pick.result if pick else None

        Board.objects.update_or_create(
            season=season, player_status=player_status, defaults=defaults
        )
        r += 1

    return True


def cache_current_board() -> bool:
    season = get_current_season()
    cache_board(season)
    return True


def cache_boards() -> bool:
    for season in Season.objects.all():
        cache_board(season)
    return True
