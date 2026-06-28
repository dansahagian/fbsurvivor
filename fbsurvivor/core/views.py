from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_POST

from fbsurvivor.core.forms import EmailForm, PickForm, PlayerForm
from fbsurvivor.core.models import (
    Board,
    MagicLink,
    Pick,
    Player,
    PlayerStatus,
    Season,
    Team,
    Week,
)
from fbsurvivor.core.queries import (
    get_current_week,
    get_locked_weeks_for_season,
    get_next_week,
    get_payouts,
    get_player_statuses_for_season_board,
    get_player_statuses_paid_for_season,
    get_player_years,
    no_picks_for_result_update,
    picks_for_player_season,
    picks_for_result_updates,
    picks_for_results,
)
from fbsurvivor.core.utils.emails import send_email, send_magic_link, send_new_player_email
from fbsurvivor.core.utils.helpers import (
    cache_board,
    can_buy_back,
    get_board,
    get_player_status,
    send_to_latest_season_played,
    update_player_records,
)
from fbsurvivor.settings import CONTACT, VENMO


class IndexView(View):
    def get(self, request):
        if request.session.get("token"):
            return redirect(reverse("board_redirect"))

        context = {"form": EmailForm()}
        return render(request, "index.html", context=context)

    def post(self, request):
        form = EmailForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email=email).first()
            if user:
                send_magic_link(user)

        return render(request, "login-sent.html")


class LoginView(View):
    def get(self, request, token):
        try:
            magic_link = MagicLink.objects.get(token=token)
        except MagicLink.DoesNotExist:
            return render(request, "login-error.html")

        if not magic_link.is_valid:
            return render(request, "login-error.html")

        magic_link.login(request)

        return redirect(reverse("board_redirect"))


@login_required
def logout_view(request):
    logout(request)
    return render(request, "logout-success.html")


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
        send_email("Survivor New Player!", [CONTACT], message)

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
        return redirect(reverse("board"))

    if can_buy_back(player_status, player, season):
        player_status.can_buy_back = False
        player_status.did_buy_back = True
        player_status.is_survivor = True
        player_status.save()
        cache_board(season)
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
        return redirect(reverse("board"))

    if can_buy_back(player_status, player, season):
        player_status.can_buy_back = False
        player_status.is_survivor = False
        player_status.save()
        cache_board(season)
        return redirect(reverse("board", args=[year]))
    else:
        return render(request, "player-buy-back-error.html", context=context)


@login_required
def payouts(request, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    context = {
        "player": player,
        "payouts": get_payouts(),
    }

    return render(request, "payouts.html", context=context)


@login_required
def rules(request, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    context = {
        "player": player,
        "contact": CONTACT,
    }

    return render(request, "rules.html", context=context)


@login_required
def seasons(request, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    context = {
        "player": player,
        "years": list(get_player_years(player)),
    }

    return render(request, "seasons.html", context=context)


@login_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def theme(request, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    player.is_dark_mode = not player.is_dark_mode
    player.save()

    return board_redirect(request)


@login_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def update_reminders(request, kind, status, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    statuses = {
        "on": True,
        "off": False,
    }

    if status not in statuses or kind != "email":
        raise Http404

    player.has_email_reminders = statuses[status]

    player.save()

    return board_redirect(request)


@login_required
def picks(request, year, **kwargs):
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
        return redirect(reverse("board", args=year))

    can_retire = player_status and (not player_status.is_retired) and season.is_current

    context["picks"] = picks_for_player_season(player, season).select_related("week", "team")
    context["status"] = "Retired" if player_status.is_retired else "Playing"
    context["can_retire"] = can_retire
    context["current"] = "picks"

    return render(request, "picks.html", context=context)


@login_required
def pick(request, year, week, **kwargs):
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

    week = get_object_or_404(Week, season=season, week_num=week)

    user_pick = get_object_or_404(Pick, player=player, week=week)
    context["pick"] = user_pick

    context["contact"] = CONTACT
    context["week"] = week.week_num
    context["team"] = None

    if user_pick.is_locked:
        return render(request, "pick-locked.html", context=context)

    if request.method == "GET":
        form = PickForm(player, season, week)
        context["form"] = form
        return render(request, "pick.html", context=context)

    if request.method == "POST":
        form = PickForm(player, season, week, request.POST)

        if form.is_valid():
            team_code = form.cleaned_data["team"]

            if team_code:
                choice = get_object_or_404(Team, team_code=team_code, season=season)
                user_pick.team = choice
                context["team"] = team_code
            else:
                user_pick.team = None

            user_pick.save()
            return render(request, "pick-submitted.html", context=context)

        else:
            return render(request, "pick-error.html", context=context)

    raise Http404


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
                player, created = Player.objects.get_or_create(user=user)
            except IntegrityError:
                return render(request, "manager-create-player-error.html")

            if created:
                send_new_player_email(user)
                return render(request, "manager-create-player-success.html")

            return render(request, "manager-create-player-error.html")


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


@staff_member_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def user_paid(request, year, username, **kwargs):
    season = get_object_or_404(Season, year=year)

    ps = get_object_or_404(PlayerStatus, player__user__username=username, season=season)
    ps.is_paid = True
    ps.save()
    cache_board(season)
    return redirect(reverse("paid", args=[year]))


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
    teams = picks_for_results(current_week) if current_week else []

    context["week"] = current_week
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

    no_picks_for_result_update(week).update(result="L")
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
