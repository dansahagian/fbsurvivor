from django.db.models import QuerySet, Sum
from django.db.models.functions import Lower
from django.utils import timezone

from fbsurvivor.core.models import Payout, Pick, Player, PlayerStatus, Season, Team, Week


def get_current_season() -> Season:
    return Season.objects.get(is_current=True)


def get_live_seasons() -> QuerySet[Season]:
    return Season.objects.filter(is_live=True).order_by("year")


def get_current_week(season: Season) -> Week | None:
    weeks = get_locked_weeks_for_season(season)
    return weeks.first() if weeks else None


def get_next_week(season: Season) -> Week | None:
    weeks = Week.objects.filter(
        season=season,
        lock_datetime__gt=timezone.now(),
    ).order_by("week_num")
    return weeks.first() if weeks else None


def get_player_years(player: Player) -> QuerySet[PlayerStatus]:
    return (
        PlayerStatus.objects.filter(player=player)
        .order_by("-season__description")
        .values_list("season__year", flat=True)
    )


def get_player_statuses_for_season_board(season: Season) -> QuerySet[PlayerStatus]:
    return (
        PlayerStatus.objects.filter(season=season)
        .annotate(lower=Lower("player__user__username"))
        .filter(is_paid=True)
        .order_by("-is_survivor", "is_retired", "-win_count", "loss_count", "lower")
        .select_related("player", "player__user")
    )


def get_player_statuses_paid_for_season(season: Season) -> QuerySet[PlayerStatus]:
    return (
        PlayerStatus.objects.filter(season=season, is_paid=False)
        .annotate(lower=Lower("player__user__username"))
        .order_by("lower")
        .prefetch_related("player", "player__user")
    )


def get_player_statuses_paid_buyback_for_season(season: Season) -> QuerySet[PlayerStatus]:
    return (
        PlayerStatus.objects.filter(season=season, did_buy_back=True, is_paid_buyback=False)
        .annotate(lower=Lower("player__user__username"))
        .order_by("lower")
        .prefetch_related("player", "player__user")
    )


def get_player_statuses_for_reminders(week: Week) -> list[PlayerStatus]:
    return list(
        week.season.player_statuses.filter(
            is_retired=False,
            player__pick__week=week,
            player__pick__team__isnull=True,
            player__has_email_reminders=True,
        ).values_list("player__user__email", flat=True)
    )


def get_locked_weeks_for_season(season: Season) -> QuerySet[Week]:
    return Week.objects.filter(season=season, lock_datetime__lte=timezone.now()).order_by(
        "-week_num"
    )


def get_payouts_current():
    season = get_current_season()

    _buy_ins = PlayerStatus.objects.filter(season=season).count()
    buy_backs = PlayerStatus.objects.filter(season=season, did_buy_back=True).count()

    survivor = 460 + (20 * buy_backs)
    best_record = 230 + (10 * buy_backs)
    survivor_bonus = 300

    return survivor, best_record, survivor_bonus


def get_payouts():
    return (
        Payout.objects.select_related("player", "player__user")
        .values("player__user__username")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )


def picks_for_player_season(player: Player, season: Season) -> QuerySet[Pick]:
    return Pick.objects.filter(player=player, week__season=season).order_by("week__week_num")


def picks_for_board(player: Player, season: Season) -> QuerySet[Pick]:
    return (
        Pick.objects.filter(player=player, week__season=season)
        .order_by("-week__week_num")
        .filter(week__lock_datetime__lte=timezone.now())
    )


def picks_for_results(week: Week) -> QuerySet[Pick]:
    return (
        Pick.objects.filter(week=week, result__isnull=True, team__isnull=False)
        .values_list("team__team_code", flat=True)
        .distinct()
    )


def picks_for_result_updates(week: Week, team: Team) -> QuerySet[Pick]:
    return Pick.objects.filter(week=week, team=team, result__isnull=True)


def no_picks_for_result_update(week: Week) -> QuerySet[Pick]:
    return Pick.objects.filter(week=week, team__isnull=True, result__isnull=True).select_related(
        "player"
    )
