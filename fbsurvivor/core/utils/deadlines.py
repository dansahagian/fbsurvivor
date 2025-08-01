from datetime import datetime

from django.utils import timezone

from fbsurvivor.core.models import Lock, Pick, PlayerStatus, Season, Week
from fbsurvivor.core.services import SeasonService, WeekQuery


def _zero_pad_number(number):
    return str(int(number)).zfill(2)


def get_countdown(deadline):
    if not deadline:
        return None

    right_now = timezone.now()

    seconds = (deadline - right_now).total_seconds()
    if seconds <= 0:
        return None

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, remainder = divmod(remainder, 60)

    d = "day" if days == 1 else "days"
    h = "hour" if hours == 1 else "hours"
    m = "minute" if minutes == 1 else "minutes"

    days = f"{int(days)} {d}" if days else ""
    hours = f"{int(hours)} {h}" if hours else ""
    minutes = f"{int(minutes)} {m}" if minutes else ""

    if days and hours and minutes:
        return f"{days}, {hours}, & {minutes}"
    elif days and (hours or minutes):
        return f"{days} & {hours}{minutes}"
    elif hours and minutes:
        return f"{hours} & {minutes}"
    else:
        return f"{hours}{minutes}"


def get_early_deadline(season: Season, next_week: Week) -> datetime | None:
    now = timezone.now()
    try:
        deadline = (
            Lock.objects.filter(week__season=season, week=next_week, lock_datetime__gte=now)
            .order_by("lock_datetime")
            .first()
        )
    except Lock.DoesNotExist:
        deadline = None

    return deadline.lock_datetime if deadline else None


def get_weekly_deadline(season: Season, next_week: Week) -> datetime | None:
    try:
        deadline = Week.objects.get(season=season, week_num=next_week.week_num)
    except Week.DoesNotExist:
        deadline = None

    return deadline.lock_datetime if deadline else None


def get_next_deadline(season):
    next_week = WeekQuery.get_next(season)
    if not next_week:
        return None

    early = get_early_deadline(season, next_week)
    weekly = get_weekly_deadline(season, next_week)

    return get_countdown(early) or get_countdown(weekly)


def get_picks_count_display(season: Season) -> str | None:
    next_week = WeekQuery.get_next(season)
    if not next_week:
        return None

    player_cnt = PlayerStatus.objects.filter(season=season, is_retired=False).count()
    pick_cnt = Pick.objects.filter(week=next_week, team__isnull=False).count()

    week = next_week.week_num

    return f"{pick_cnt} / {player_cnt} players have made their Week {week} pick."


def get_reminder_message(season: Season, next_week: Week) -> str | None:
    now = timezone.now()

    early_locks = Lock.objects.filter(
        week__season=season, week=next_week, lock_datetime__gte=now
    ).order_by("lock_datetime")

    results = {}

    for lock in early_locks:
        if results.get(lock.lock_datetime):
            results[lock.lock_datetime].append(lock.team.team_code)
        else:
            results[lock.lock_datetime] = [lock.team.team_code]

    message = ""

    for result in results:
        teams = ", ".join(results[result])
        message += f"{teams}: {get_countdown(result)}\n\n"

    weekly_deadline = get_weekly_deadline(season, next_week)
    if weekly_deadline:
        message += f"All Teams: {get_countdown(weekly_deadline)}\n\n"

    if message:
        live_seasons = "\n- ".join([x.description for x in SeasonService.get_live()])
        message += f"You are missing a pick in one of the following seasons:\n- {live_seasons}"

    return message if message else None
