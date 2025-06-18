from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from fbsurvivor.core.forms import EmailForm, PickForm
from fbsurvivor.core.models import (
    LoggedOutTokens,
    MagicLink,
    Pick,
    Player,
    PlayerStatus,
    Season,
    Team,
    Week,
)
from fbsurvivor.core.services import PayoutQuery, PickQuery, PlayerStatusQuery, WeekQuery
from fbsurvivor.core.utils.auth import (
    authenticate_admin,
    authenticate_player,
    create_token,
    get_season_context,
    send_magic_link,
)
from fbsurvivor.core.utils.emails import send_email
from fbsurvivor.core.utils.helpers import (
    cache_board,
    can_buy_back,
    get_board,
    get_player_context,
    send_to_latest_season_played,
    update_player_records,
)
from fbsurvivor.settings import CONTACT


def login(request):
    if request.method == "GET":
        if request.session.get("token"):
            return redirect(reverse("board_redirect"))

        context = {
            "form": EmailForm(),
        }
        return render(request, "fbsurvivor/templates/login.html", context=context)

    if request.method == "POST":
        form = EmailForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                player = Player.objects.get(email=email)
                send_magic_link(player)
            except Player.DoesNotExist:
                pass

        return render(request, "fbsurvivor/templates/login-sent.html")


def enter(request, magic_link_id):
    try:
        magic_link = MagicLink.objects.get(id=magic_link_id)
    except MagicLink.DoesNotExist:
        return render(request, "fbsurvivor/templates/error-magic-link.html")

    if magic_link.is_expired:
        render(request, "fbsurvivor/templates/error-magic-link.html")

    token = create_token(magic_link.player)
    magic_link.delete()
    request.session["token"] = token

    return redirect(reverse("board_redirect"))


@authenticate_player
def logout(request, **kwargs):
    token = request.session["token"]
    LoggedOutTokens.objects.create(id=token)
    request.session.delete("token")
    return redirect(reverse("login"))


@authenticate_admin
def assume(request, username, **kwargs):
    player = get_object_or_404(Player, username=username)
    token = create_token(player)
    request.session["token"] = token
    return redirect(reverse("board_redirect"))


@authenticate_player
def board_redirect(request, **kwargs):
    current_season = Season.objects.get(is_current=True)

    return redirect(reverse("board", args=[current_season.year]))


@authenticate_player
def board(request, year: int, **kwargs):
    player = kwargs["player"]
    season, player_status, context = get_player_context(player, year)

    if season.is_locked and not player_status:
        return send_to_latest_season_played(request, player)

    can_play = not player_status and not season.is_locked
    weeks = WeekQuery.for_display(season).order_by("-week_num").values_list("week_num", flat=True)

    player_statuses_count = PlayerStatusQuery.for_season_board(season).count()
    season_board = get_board(season)

    next_week = WeekQuery.get_next(season)

    context["next_week"] = None
    if next_week:
        try:
            player_pick = Pick.objects.get(player=player, week=next_week)
            next_pick = player_pick.team.team_code if player_pick.team else "None"
            context["next_week"] = next_week.week_num
            context["next_pick"] = next_pick
        except Pick.DoesNotExist:
            context["next_pick"] = None

    context.update(
        {
            "can_play": can_play,
            "weeks": weeks,
            "board": season_board,
            "player_count": player_statuses_count,
            "can_buy_back": can_buy_back(player_status, player, season),
        }
    )

    return render(request, "board.html", context=context)


@authenticate_player
def play(request, year: int, **kwargs):
    player = kwargs["player"]
    season, player_status, context = get_player_context(player, year)

    if player_status:
        return redirect(reverse("board", args=[year]))

    if season.is_locked:
        return send_to_latest_season_played(request, player)

    context.update(
        {
            "player": player,
            "season": season,
            "contact": CONTACT,
        }
    )

    if request.method == "GET":
        return render(request, "confirm.html", context=context)

    if request.method == "POST":
        PlayerStatus.objects.create(player=player, season=season)
        weeks = Week.objects.filter(season=season)
        player_picks = [Pick(player=player, week=week) for week in weeks]
        Pick.objects.bulk_create(player_picks)
        cache_board(season)

        recipient = Player.objects.get(username="DanTheAutomator").email
        message = f"{player.username} in for {season.year}"
        send_email("Survivor New Player!", [recipient], message)

        return redirect(reverse("board", args=[year]))


@authenticate_player
def buy_back(request, year: int, **kwargs):
    player = kwargs["player"]
    season, player_status, context = get_player_context(player, year)
    if not player_status:
        return redirect(reverse("board"))

    if can_buy_back(player_status, player, season):
        player_status.did_buy_back = True
        player_status.is_survivor = True
        player_status.is_paid = False
        player_status.save()
        return redirect(reverse("board", args=[year]))
    else:
        return render(request, "error-buy-back.html", context=context)


@authenticate_player
def payouts(request, **kwargs):
    player = kwargs["player"]
    player_payouts = PayoutQuery.for_payout_table()

    context = {
        "player": player,
        "payouts": player_payouts,
    }

    return render(request, "payouts.html", context=context)


@authenticate_player
def rules(request, **kwargs):
    player = kwargs["player"]

    context = {
        "player": player,
        "contact": CONTACT,
    }

    return render(request, "rules.html", context=context)


@authenticate_player
def seasons(request, **kwargs):
    player = kwargs["player"]

    years = list(PlayerStatusQuery.player_years(player))

    context = {
        "player": player,
        "years": years,
    }

    return render(request, "seasons.html", context=context)


@authenticate_player
def theme(request, **kwargs):
    player = kwargs["player"]
    player.is_dark_mode = not player.is_dark_mode
    player.save()

    return board_redirect(request)


@authenticate_player
def update_reminders(request, kind, status, **kwargs):
    player = kwargs["player"]

    statuses = {
        "on": True,
        "off": False,
    }

    if status not in statuses or kind != "email":
        raise Http404

    player.has_email_reminders = statuses[status]

    player.save()

    return board_redirect(request)


@authenticate_player
def picks(request, year, **kwargs):
    player = kwargs["player"]
    season, player_status, context = get_player_context(player, year)

    if not player_status:
        return redirect(reverse("board", args=year))

    can_retire = player_status and (not player_status.is_retired) and season.is_current

    context["picks"] = (
        PickQuery.for_player_season(player, season).select_related("week").select_related("team")
    )
    context["status"] = "Retired" if player_status.is_retired else "Playing"
    context["can_retire"] = can_retire
    context["current"] = "picks"

    return render(request, "picks.html", context=context)


@authenticate_player
def pick(request, year, week, **kwargs):
    player = kwargs["player"]
    season, _player_status, context = get_player_context(player, year)

    week = get_object_or_404(Week, season=season, week_num=week)

    user_pick = get_object_or_404(Pick, player=player, week=week)
    context["pick"] = user_pick

    if user_pick.is_locked:
        return render(request, "error-pick.html", context=context)

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
            else:
                user_pick.team = None
            user_pick.save()
        else:
            return render(request, "error-pick.html", context=context)

        return redirect(reverse("board", args=[year]))


@authenticate_admin
def manager(request, year, **kwargs):
    _season, context = get_season_context(year, **kwargs)
    return render(request, "manager.html", context=context)


@authenticate_admin
def paid(request, year, **kwargs):
    season, context = get_season_context(year, **kwargs)
    player_statuses = PlayerStatusQuery.paid_for_season(season).prefetch_related("player")
    context["player_statuses"] = player_statuses
    return render(request, "paid.html", context=context)


@authenticate_admin
def user_paid(request, year, username, **kwargs):
    season, _context = get_season_context(year, **kwargs)
    ps = get_object_or_404(PlayerStatus, player__username=username, season=season)
    ps.is_paid = True
    ps.save()
    return redirect(reverse("paid", args=[year]))


@authenticate_admin
def results(request, year, **kwargs):
    season, context = get_season_context(year, **kwargs)
    current_week = WeekQuery.get_current(season)
    teams = PickQuery.for_results(current_week)

    context["week"] = current_week
    context["teams"] = teams

    return render(request, "results.html", context=context)


@authenticate_admin
def result(request, year, week, team, outcome, **kwargs):
    season, _context = get_season_context(year, **kwargs)
    week = get_object_or_404(Week, season=season, week_num=week)

    team = get_object_or_404(Team, team_code=team, season=season)
    PickQuery.for_result_updates(week, team).update(result=outcome)
    PickQuery.for_no_picks(week).update(result="L")

    _player_records_updated = update_player_records(year)
    cache_board(season)

    return redirect(reverse("results", args=[year]))


@authenticate_admin
def get_players(request, year, **kwargs):
    _season, context = get_season_context(year, **kwargs)
    context["players"] = (
        Player.objects.values_list("username", flat=True).distinct().order_by("username")
    )

    return render(request, "players.html", context=context)
