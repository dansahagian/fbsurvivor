from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from fbsurvivor.core.forms import EmailForm, MessageForm, PickForm
from fbsurvivor.core.models import (
    Pick,
    Player,
    PlayerStatus,
    Season,
    Team,
    TokenHash,
    Week,
)
from fbsurvivor.core.services import PayoutQuery, PickQuery, PlayerStatusQuery, WeekQuery
from fbsurvivor.core.utils.auth import (
    authenticate_admin,
    authenticate_player,
    create_token,
    get_season_context,
    get_token_hash,
    send_magic_link,
)
from fbsurvivor.core.utils.emails import send_email
from fbsurvivor.core.utils.helpers import (
    cache_board,
    get_add_on_season,
    get_board,
    get_player_context,
    send_to_latest_season_played,
    update_player_records,
)
from fbsurvivor.core.utils.reminders import send_reminders
from fbsurvivor.settings import CONTACT, VENMO


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


def enter(request, token):
    request.session["token"] = token

    return redirect(reverse("board_redirect"))


@authenticate_player
def logout(request, **kwargs):
    if token := request.session.get("token"):
        TokenHash.objects.get(hash=get_token_hash(token)).delete()
    request.session.delete("token")
    return redirect(reverse("login"))


@authenticate_admin
def assume(request, username, **kwargs):
    player = get_object_or_404(Player, username=username)
    token = create_token(player)

    return redirect(reverse("enter", args=[token]))


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

    try:
        playable = Season.objects.get(is_locked=False).year
    except Season.DoesNotExist:
        playable = None

    context["next_week"] = None
    if next_week := WeekQuery.get_next(season):
        try:
            player_pick = Pick.objects.get(player=player, week=next_week)
            next_pick = player_pick.team.team_code if player_pick.team else "None"
            context["next_week"] = next_week.week_num
            context["next_pick"] = next_pick
        except Pick.DoesNotExist:
            context["next_pick"] = None

    add_on_season = get_add_on_season(player, season)

    context.update(
        {
            "can_play": can_play,
            "weeks": weeks,
            "board": season_board,
            "player_count": player_statuses_count,
            "playable": playable,
            "venmo": VENMO,
            "add_on_season": add_on_season,
        }
    )

    return render(request, "board.html", context=context)


@authenticate_player
def play(request, year: int, **kwargs):
    player = kwargs["player"]
    season, player_status, context = get_player_context(player, year)

    if player_status:
        messages.info(request, f"You are already playing for {year}!")
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
        messages.info(request, f"Good luck in the {year} season!")

        recipient = Player.objects.get(username="DanTheAutomator").email
        message = f"{player.username} in for {season.year}"
        send_email("Survivor New Player!", [recipient], message)

        return redirect(reverse("board", args=[year]))


@authenticate_player
def retire(request, year, **kwargs):
    player = kwargs["player"]
    season, player_status, _context = get_player_context(player, year)

    if not player_status:
        messages.info(request, "You can NOT retire from a season you didn't play!")
    elif player_status.is_retired:
        messages.info(request, f"You already retired in {year}!")
    elif not season.is_current:
        messages.info(request, "You can NOT retire from a past season!")
    else:
        player_status.is_retired = True
        player_status.save()
        Pick.objects.filter(player=player, week__season=season, result__isnull=True).update(
            result="R"
        )
        cache_board(season)
        messages.info(request, "You have retired. See you next year!")

    return redirect(reverse("board", args=[year]))


@authenticate_player
def more(request, **kwargs):
    player = kwargs["player"]

    context = {
        "player": player,
    }
    return render(request, "more.html", context=context)


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
def reminders(request, **kwargs):
    player = kwargs["player"]

    context = {
        "player": player,
        "contact": CONTACT,
    }

    return render(request, "reminders.html", context=context)


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

    return redirect(reverse("reminders"))


@authenticate_player
def picks(request, year, **kwargs):
    player = kwargs["player"]
    season, player_status, context = get_player_context(player, year)

    if not player_status:
        messages.info(request, "You must play this season before editing picks!")
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
        messages.info(request, f"Week {week.week_num} is locked!")
        return redirect(reverse("picks", args=[year]))

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
                messages.info(request, f"{team_code} submitted for week {week.week_num}")
            else:
                user_pick.team = None
                messages.info(request, f"No team submitted for week {week.week_num}")
            user_pick.save()
        else:
            messages.info(request, "Bad form submission")

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
    messages.info(request, f"{ps.player.username} marked as paid!")
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

    messages.info(request, f"Picks for week {week.week_num} of {team} updated!")

    player_records_updated = update_player_records(year)
    cache_board(season)
    messages.info(request, f"{player_records_updated} player records updated!")

    return redirect(reverse("results", args=[year]))


@authenticate_admin
def remind(request, year, **kwargs):
    send_reminders()
    messages.info(request, "Reminder task kicked off")
    return redirect(reverse("manager", args=[year]))


@authenticate_admin
def get_players(request, year, **kwargs):
    _season, context = get_season_context(year, **kwargs)
    context["players"] = (
        Player.objects.values_list("username", flat=True).distinct().order_by("username")
    )

    return render(request, "players.html", context=context)


@authenticate_admin
def send_message(request, year, **kwargs):
    season, context = get_season_context(year, **kwargs)

    if request.method == "GET":
        context["form"] = MessageForm()
        return render(request, "message.html", context=context)

    if request.method == "POST":
        form = MessageForm(request.POST)

        if form.is_valid():
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            recipients = list(
                Player.objects.filter(playerstatus__season=season)
                .exclude(email="")
                .values_list("email", flat=True)
            )

            send_email(subject, recipients, message)

            return redirect(reverse("board", args=[year]))


@authenticate_admin
def send_message_all(request, **kwargs):
    if request.method == "GET":
        context = {"form": MessageForm()}
        return render(request, "message_all.html", context=context)

    if request.method == "POST":
        form = MessageForm(request.POST)

        if form.is_valid():
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]

            recipients = list(Player.objects.exclude(email="").values_list("email", flat=True))

            send_email(subject, recipients, message)

            return redirect(reverse("board_redirect"))
