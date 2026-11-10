from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from fbsurvivor.core.models import Pick, Player, PlayerStatus, Season, Week
from fbsurvivor.core.queries import (
    get_locked_weeks_for_season,
    get_next_week,
    get_player_statuses_for_season_board,
)
from fbsurvivor.core.utils.emails import send_addressed_email
from fbsurvivor.core.utils.helpers import (
    cache_board,
    can_buy_back,
    get_board,
    get_player_status,
    send_to_latest_season_played,
)
from fbsurvivor.settings import CONTACT, VENMO


@login_required
def board_redirect(request, **kwargs):
    current_season = Season.objects.get(is_current=True)

    return redirect(reverse("board", args=[current_season.year]))


@login_required
def board(request, year: int, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)
    player_status = get_player_status(player, season)

    context = {
        "user": user,
        "player": player,
        "season": season,
        "player_status": player_status,
        "venmo": VENMO,
        "contact": CONTACT,
    }

    if not player_status:
        if season.is_locked:
            return render(request, "board-error.html", context=context)
        else:
            context["player_count"] = get_player_statuses_for_season_board(season).count()
            return render(request, "player-play.html", context=context)

    if not player_status.is_paid:
        return render(request, "player-pay.html", context=context)

    if can_buy_back(player_status, player, season):
        return render(request, "player-buy-back.html", context=context)

    weeks = get_locked_weeks_for_season(season).values_list("week_num", flat=True)
    season_board = get_board(season)

    next_week = get_next_week(season)

    context["next_week"] = None
    if next_week:
        try:
            player_pick = Pick.objects.get(player=player, week=next_week)
            next_pick = player_pick.team.team_code if player_pick.team else "None"
            context["next_week"] = next_week.week_num
            context["next_pick"] = next_pick
        except Pick.DoesNotExist:
            context["next_pick"] = None

    context.update({"weeks": weeks, "board": season_board})

    return render(request, "board.html", context=context)


@login_required
def play(request, year: int, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)
    player_status = get_player_status(player, season)

    context = {
        "user": user,
        "player": player,
        "season": season,
        "player_status": player_status,
    }

    if player_status:
        return redirect(reverse("board", args=[year]))

    if season.is_locked:
        return send_to_latest_season_played(request, player)

    context.update({"player": player, "season": season, "contact": CONTACT})

    if request.method == "GET":
        return render(request, "player-accept-rules.html", context=context)

    if request.method == "POST":
        PlayerStatus.objects.create(player=player, season=season)
        weeks = Week.objects.filter(season=season)
        player_picks = [Pick(player=player, week=week) for week in weeks]
        Pick.objects.bulk_create(player_picks)
        cache_board(season)

        message = f"{user.username} in for {season.year}"
        send_addressed_email("Survivor New Player!", CONTACT, message)

        return redirect(reverse("board", args=[year]))

    raise Http404


@login_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def buy_back(request, year: int, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)
    player_status = get_player_status(player, season)

    context = {
        "user": user,
        "player": player,
        "season": season,
        "player_status": player_status,
    }

    if not player_status:
        return redirect(reverse("board_redirect"))

    if can_buy_back(player_status, player, season):
        player_status.can_buy_back = False
        player_status.did_buy_back = True
        player_status.is_survivor = True
        player_status.save()
        cache_board(season)

        message = f"{user.username} for {season.year}"
        send_addressed_email("Survivor Buy-Back Accepted", CONTACT, message)

        return redirect(reverse("board", args=[year]))
    else:
        return render(request, "player-buy-back-error.html", context=context)


@login_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def decline_buy_back(request, year: int, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)
    player_status = get_player_status(player, season)

    context = {
        "user": user,
        "player": player,
        "season": season,
        "player_status": player_status,
    }

    if not player_status:
        return redirect(reverse("board_redirect"))

    if can_buy_back(player_status, player, season):
        player_status.can_buy_back = False
        player_status.is_survivor = False
        player_status.save()
        cache_board(season)

        message = f"{user.username} for {season.year}"
        send_addressed_email("Survivor Buy-Back Declined", CONTACT, message)

        return redirect(reverse("board", args=[year]))
    else:
        return render(request, "player-buy-back-error.html", context=context)
