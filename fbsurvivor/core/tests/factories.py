import factory.django
from django.utils import timezone
from factory.declarations import LazyAttribute, Sequence, SubFactory

from fbsurvivor.core.models import Pick, Player, PlayerStatus, Season, Team, Week


class PlayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Player

    username = Sequence(lambda n: f"Player{n + 1}")
    email = LazyAttribute(lambda a: f"{a.username}@fbsurvivor.com")
    has_email_reminders = True


class SeasonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Season

    year = Sequence(lambda n: n + 2017)
    is_locked = True
    is_current = False


class WeekFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Week

    season = SubFactory(SeasonFactory)
    week_num = Sequence(lambda n: n + 1)
    lock_datetime = timezone.now()


class TeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Team

    season = SubFactory(SeasonFactory)
    team_code = Sequence(lambda n: f"T{n + 1}")
    bye_week = Sequence(lambda n: n + 1)


class PickFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pick

    player = SubFactory(PlayerFactory)
    week = SubFactory(WeekFactory)
    team = SubFactory(TeamFactory)


class PlayerStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PlayerStatus

    player = SubFactory(PlayerFactory)
    season = SubFactory(SeasonFactory)
