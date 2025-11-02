from django.utils import timezone
from factory.declarations import LazyAttribute, Sequence, SubFactory
from factory.django import DjangoModelFactory

from fbsurvivor.core.models import Pick, Player, PlayerStatus, Season, Team, Week


class PlayerFactory(DjangoModelFactory):
    # pyrefly: ignore  # bad-override
    class Meta:
        model = Player

    username = Sequence(lambda n: f"Player{n + 1}")
    email = LazyAttribute(lambda a: f"{a.username}@fbsurvivor.com")
    has_email_reminders = True


class SeasonFactory(DjangoModelFactory):
    # pyrefly: ignore  # bad-override
    class Meta:
        model = Season

    year = Sequence(lambda n: n + 2017)
    is_locked = True
    is_current = False


class WeekFactory(DjangoModelFactory):
    # pyrefly: ignore  # bad-override
    class Meta:
        model = Week

    season = SubFactory(SeasonFactory)
    week_num = Sequence(lambda n: n + 1)
    lock_datetime = timezone.now()


class TeamFactory(DjangoModelFactory):
    # pyrefly: ignore  # bad-override
    class Meta:
        model = Team

    season = SubFactory(SeasonFactory)
    team_code = Sequence(lambda n: f"T{n + 1}")
    bye_week = Sequence(lambda n: n + 1)


class PickFactory(DjangoModelFactory):
    # pyrefly: ignore  # bad-override
    class Meta:
        model = Pick

    player = SubFactory(PlayerFactory)
    week = SubFactory(WeekFactory)
    team = SubFactory(TeamFactory)


class PlayerStatusFactory(DjangoModelFactory):
    # pyrefly: ignore  # bad-override
    class Meta:
        model = PlayerStatus

    player = SubFactory(PlayerFactory)
    season = SubFactory(SeasonFactory)
