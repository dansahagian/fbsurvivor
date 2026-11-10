from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from fbsurvivor.core.models import Player
from fbsurvivor.core.queries import get_payouts, get_payouts_current, get_player_years
from fbsurvivor.settings import CONTACT


@login_required
def payouts_current(request, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    survivor, best_record, survivor_bonus = get_payouts_current()

    context = {
        "player": player,
        "survivor_payout": survivor,
        "record_payout": best_record,
        "bonus_payout": survivor_bonus,
    }

    return render(request, "payouts_current.html", context=context)


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
