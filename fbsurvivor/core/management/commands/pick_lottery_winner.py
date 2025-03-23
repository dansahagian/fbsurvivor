from secrets import choice

from django.core.management.base import BaseCommand
from django.db.models.functions import Lower

from fbsurvivor.core.models import PlayerStatus, Season


class Command(BaseCommand):
    help = "Pick the winner of free entry for next season"

    def add_arguments(self, parser):
        parser.add_argument("year", type=int)

    def handle(self, *args, **options):
        year = options["year"]
        season = Season.objects.get(year=year)

        # filter out players who don't have full picks, have won money, and me
        ps = (
            PlayerStatus.objects.filter(
                season=season,
                has_complete_picks=True,
                has_won_gt_buy_in=False,
                is_retired=False,
            )
            .exclude(player__username="DanTheAutomator")
            .annotate(lower=Lower("player__username"))
            .prefetch_related("player")
            .order_by("-win_count", "lower")
        )

        hat = []
        for p in ps:  # type: ignore
            hat.extend([p.player.username] * p.win_count)

        total = len(hat)
        for p in ps:  # type: ignore
            print(f"{p.player}: {round(p.win_count / total * 100, 2)}%")

        print(f"And the winner is... {choice(hat)}\n\n")
