import arrow

from fbsurvivor import settings
from fbsurvivor.core.models import Player, Season, Week
from fbsurvivor.core.utils.emails import send_email


class PlayerService:
    @staticmethod
    def create(username: str, email: str):
        player, created = Player.objects.get_or_create(username=username, email=email)

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
            self.season: Season.objects.get(year=season)
        else:
            self.season = None

    @staticmethod
    def get_live():
        return Season.objects.filter(is_live=True)

    def get_next_week(self):
        weeks = Week.objects.filter(
            season=self.season,
            lock_datetime__gt=arrow.now().datetime,
        ).order_by("week_num")

        return weeks.first() if weeks else None
