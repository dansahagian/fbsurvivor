from django.db.models.aggregates import Sum
from django.db.models.functions import Lower
from django.utils import timezone

from fbsurvivor import settings
from fbsurvivor.core.models import Payout, Pick, Player, PlayerStatus, Season, Week
from fbsurvivor.core.utils.emails import send_email


class PlayerService:
    @staticmethod
    def create(username: str, email: str):
        _, created = Player.objects.get_or_create(username=username, email=email)

        if created:
            ps = f"If you didn't sign up, please email Dan at {settings.CONTACT}"
            login = f"{settings.DOMAIN}"
            subject = "Survivor User Account"
            recipients = [email]
            message = f"You can login here:\n\n{login}\n\n{ps}"

            send_email(subject, recipients, message)


class SeasonService:
    def __init__(self, season: int | Season | None = None):
        if isinstance(season, Season):
            self.season = season
        elif isinstance(season, int):
            self.season = Season.objects.get(year=season)
        else:
            self.season = None

    @staticmethod
    def get_current():
        return Season.objects.get(is_current=True)

    @staticmethod
    def get_live():
        return Season.objects.filter(is_live=True).order_by("year")

    def get_next_week(self):
        weeks = Week.objects.filter(
            season=self.season,
            lock_datetime__gt=timezone.now(),
        ).order_by("week_num")

        return weeks.first() if weeks else None


class PlayerStatusQuery:
    @staticmethod
    def player_years(player):
        return (
            PlayerStatus.objects.filter(player=player)
            .order_by("-season__description")
            .values_list("season__year", flat=True)
        )

    @staticmethod
    def for_season_board(season):
        return (
            PlayerStatus.objects.filter(season=season)
            .annotate(lower=Lower("player__username"))
            .order_by("-is_survivor", "is_retired", "-win_count", "loss_count", "lower")
        )

    @staticmethod
    def paid_for_season(season):
        return (
            PlayerStatus.objects.filter(season=season)
            .annotate(lower=Lower("player__username"))
            .order_by("-is_paid", "lower")
        )

    @staticmethod
    def for_reminders(week):
        return PlayerStatus.objects.filter(
            season=week.season,
            is_retired=False,
            player__pick__week=week,
            player__pick__team__isnull=True,
        )

    @staticmethod
    def for_email_reminders(week):
        return (
            PlayerStatusQuery.for_reminders(week)
            .filter(player__has_email_reminders=True)
            .values_list("player__email", flat=True)
        )


class WeekQuery:
    @staticmethod
    def for_display(season):
        return Week.objects.filter(
            season=season,
            lock_datetime__lte=timezone.now(),
        ).order_by("week_num")

    @staticmethod
    def get_current(season):
        qs = WeekQuery.for_display(season)
        return qs.last() if qs else None

    @staticmethod
    def get_next(season):
        qs = Week.objects.filter(
            season=season,
            lock_datetime__gt=timezone.now(),
        ).order_by("week_num")
        return qs.first() if qs else None


class PayoutQuery:
    @staticmethod
    def for_payout_table():
        return (
            Payout.objects.values("player")
            .annotate(total=Sum("amount"))
            .order_by("-total")
            .values("player__username", "total", "player__notes")
        )


class PickQuery:
    @staticmethod
    def for_player_season(player, season):
        return Pick.objects.filter(player=player, week__season=season).order_by("week__week_num")

    @staticmethod
    def for_board(player, season):
        return (
            PickQuery.for_player_season(player, season)
            .order_by("-week__week_num")
            .filter(
                week__lock_datetime__lte=timezone.now(),
            )
        )

    @staticmethod
    def for_results(week):
        return (
            Pick.objects.filter(week=week, result__isnull=True, team__isnull=False)
            .values_list("team__team_code", flat=True)
            .distinct()
        )

    @staticmethod
    def for_result_updates(week, team):
        return Pick.objects.filter(week=week, team=team, result__isnull=True)

    @staticmethod
    def for_no_picks(week):
        return Pick.objects.filter(week=week, team__isnull=True, result__isnull=True)
