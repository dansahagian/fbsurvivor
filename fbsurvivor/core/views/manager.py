from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from fbsurvivor.core.forms import PlayerForm
from fbsurvivor.core.models import Board, Player, PlayerStatus, Season, Team, Week
from fbsurvivor.core.queries import (
    get_current_week,
    get_player_statuses_paid_buyback_for_season,
    get_player_statuses_paid_for_season,
    no_picks_for_result_update,
    picks_for_result_updates,
    picks_for_results,
)
from fbsurvivor.core.utils.emails import send_new_player_email
from fbsurvivor.core.utils.helpers import cache_board, update_player_records


@staff_member_required
def manager(request, year, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)

    context = {
        "user": user,
        "player": player,
        "season": season,
    }

    return render(request, "manager.html", context=context)


@staff_member_required
def create_player(request, **kwargs):
    if request.method == "GET":
        context = {"form": PlayerForm()}
        return render(request, "manager-create-player.html", context=context)

    if request.method == "POST":
        form = PlayerForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]

            try:
                user = User.objects.create(username=username, email=email)
                _player, created = Player.objects.get_or_create(user=user)
            except IntegrityError:
                return render(request, "manager-create-player-error.html")

            if created:
                send_new_player_email(user)
                return render(request, "manager-create-player-success.html")

            return render(request, "manager-create-player-error.html")

        return render(request, "manager-create-player.html", context={"form": form})


@staff_member_required
def paid(request, year, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)

    context = {
        "user": user,
        "player": player,
        "season": season,
    }

    context["player_statuses"] = get_player_statuses_paid_for_season(season)
    return render(request, "manager-paid.html", context=context)


@staff_member_required
def paid_buyback(request, year, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)

    context = {
        "user": user,
        "player": player,
        "season": season,
    }

    context["player_statuses"] = get_player_statuses_paid_buyback_for_season(season)
    return render(request, "manager-paid-buyback.html", context=context)


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def user_paid(request, year, username, **kwargs):
    season = get_object_or_404(Season, year=year)

    ps = get_object_or_404(PlayerStatus, player__user__username=username, season=season)
    ps.is_paid = True
    ps.save()
    cache_board(season)
    return redirect(reverse("paid", args=[year]))


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def user_paid_buyback(request, year, username, **kwargs):
    season = get_object_or_404(Season, year=year)

    ps = get_object_or_404(PlayerStatus, player__user__username=username, season=season)
    ps.is_paid_buyback = True
    ps.save()
    cache_board(season)
    return redirect(reverse("paid_buyback", args=[year]))


@staff_member_required
def results(request, year, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)

    context = {
        "user": user,
        "player": player,
        "season": season,
    }

    current_week = get_current_week(season)
    if current_week:
        no_picks = no_picks_for_result_update(current_week).count()
        teams = picks_for_results(current_week)
    else:
        no_picks = 0
        teams = []

    context["week"] = current_week
    context["no_picks"] = no_picks > 0
    context["teams"] = teams

    return render(request, "manager-results.html", context=context)


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def result(request, year, week, team, outcome, **kwargs):
    if outcome not in ("W", "L"):
        raise Http404

    season = get_object_or_404(Season, year=year)
    week = get_object_or_404(Week, season=season, week_num=week)
    team = get_object_or_404(Team, team_code=team, season=season)

    weekly_picks = picks_for_result_updates(week, team)

    # if it's a loss, query for the player statuses and set the is_survivor flag to false
    if outcome == "L":
        PlayerStatus.objects.filter(player__pick__in=weekly_picks, season=season).update(
            is_survivor=False
        )

    weekly_picks.update(result=outcome)
    _player_records_updated = update_player_records(year)
    cache_board(season)

    return redirect(reverse("results", args=[year]))


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def result_no_pick(request, year, week, **kwargs):
    season = get_object_or_404(Season, year=year)
    week = get_object_or_404(Week, season=season, week_num=week)

    no_picks = no_picks_for_result_update(week)
    players = [x.player for x in no_picks]
    no_picks.update(result="L")

    PlayerStatus.objects.filter(player__in=players, season=season).update(is_survivor=False)

    _player_records_updated = update_player_records(year)
    cache_board(season)

    return redirect(reverse("results", args=[year]))


@staff_member_required
def get_players(request, year, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)
    season = get_object_or_404(Season, year=year)

    context = {
        "user": user,
        "player": player,
        "season": season,
    }

    context["players"] = (
        Player.objects.values_list("user__username", flat=True)
        .distinct()
        .order_by("user__username")
    )

    return render(request, "manager-players.html", context=context)


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def assume_player(request, username: str):
    user = User.objects.get(username=username)
    login(request, user)

    return redirect(reverse("board_redirect"))


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def cache_season(request, year, **kwargs):
    season = get_object_or_404(Season, year=year)

    Board.objects.filter(season=season).delete()
    cache_board(season)

    return redirect(reverse("board", args=[season.year]))
