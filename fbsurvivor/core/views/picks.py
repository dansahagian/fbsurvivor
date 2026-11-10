from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from fbsurvivor.core.forms import PickForm
from fbsurvivor.core.models import Pick, Player, Season, Team, Week
from fbsurvivor.core.queries import picks_for_player_season
from fbsurvivor.core.utils.helpers import get_player_status
from fbsurvivor.settings import CONTACT


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
        return redirect(reverse("board_redirect"))

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
