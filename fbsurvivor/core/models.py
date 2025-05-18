import arrow
from django.db import models
from django.utils import timezone


class Player(models.Model):
    username = models.CharField(max_length=20, unique=True)
    email = models.CharField(max_length=100, blank=True, default="")

    emoji = models.CharField(max_length=8, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    is_admin = models.BooleanField(default=False)
    is_dark_mode = models.BooleanField(default=False)

    has_email_reminders = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["username"]), models.Index(fields=["email"])]

    def __str__(self):
        return f"{self.username}"


class MagicLink(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="magic_links",
        related_query_name="magic_link",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        expiration_time = self.created_at + timezone.timedelta(minutes=30)
        return timezone.now() > expiration_time


class LoggedOutTokens(models.Model):
    id = models.CharField(max_length=1024, primary_key=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Season(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    description = models.CharField(max_length=16, default="")
    is_locked = models.BooleanField(default=True)
    is_current = models.BooleanField(default=False)
    is_live = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.year}"

    class Meta:
        ordering = ["-year"]
        indexes = [models.Index(fields=["year"])]


class PlayerStatus(models.Model):
    player = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    season = models.ForeignKey(Season, on_delete=models.DO_NOTHING)
    is_paid = models.BooleanField(default=False)
    is_retired = models.BooleanField(default=False)
    is_survivor = models.BooleanField(default=True)
    did_buy_back = models.BooleanField(default=False)
    win_count = models.SmallIntegerField(default=0)
    loss_count = models.SmallIntegerField(default=0)

    def __str__(self):
        return f"{self.player} - {self.season}"

    class Meta:
        models.UniqueConstraint(fields=["player", "season"], name="unique_playerstatus")
        verbose_name_plural = "playerstatuses"
        indexes = [models.Index(fields=["player", "season"])]


class Payout(models.Model):
    player = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    season = models.ForeignKey(Season, on_delete=models.DO_NOTHING)
    amount = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return f"{self.player} - {self.season} - {self.amount}"

    class Meta:
        models.UniqueConstraint(fields=["player", "season"], name="unique_payout")
        verbose_name_plural = "payouts"


class Week(models.Model):
    season = models.ForeignKey(Season, on_delete=models.DO_NOTHING)
    week_num = models.PositiveSmallIntegerField(db_index=True)
    lock_datetime = models.DateTimeField(db_index=True, null=True)

    @property
    def is_locked(self):
        return arrow.now() > self.lock_datetime if self.lock_datetime else False

    def __str__(self):
        return f"{self.season} | {self.week_num}"

    class Meta:
        models.UniqueConstraint(fields=["season", "week_num"], name="unique_week")


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.DO_NOTHING)
    team_code = models.CharField(max_length=3)
    name = models.CharField(max_length=15, default="")
    bye_week = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.season} | {self.team_code}"

    class Meta:
        models.UniqueConstraint(fields=["season", "team_code"], name="unique_team")
        ordering = ["-season", "team_code"]

    def is_locked(self, week: Week) -> bool:
        try:
            lock = Lock.objects.get(week=week, team=self)
            return arrow.now() > lock.lock_datetime if lock.lock_datetime else False
        except Lock.DoesNotExist:
            return week.is_locked


class Lock(models.Model):
    week = models.ForeignKey("core.Week", on_delete=models.CASCADE)
    team = models.ForeignKey("core.Team", on_delete=models.CASCADE)
    lock_datetime = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.week} | {self.team}"

    class Meta:
        models.UniqueConstraint(fields=["week", "team"], name="unique_lock")


class Pick(models.Model):
    result_choices = [
        ("W", "WIN"),
        ("L", "LOSS"),
        ("R", "RETIRED"),
        (None, "None"),
    ]
    player = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    week = models.ForeignKey(Week, on_delete=models.DO_NOTHING)
    team = models.ForeignKey(Team, on_delete=models.DO_NOTHING, null=True)
    result = models.CharField(choices=result_choices, max_length=1, null=True, blank=True)

    @property
    def is_locked(self):
        try:
            lock = Lock.objects.get(week=self.week, team=self.team)
            return arrow.now() > lock.lock_datetime if lock.lock_datetime else False
        except Lock.DoesNotExist:
            return self.week.is_locked

    @property
    def deadline(self):
        try:
            lock = Lock.objects.get(week=self.week, team=self.team)
            return lock.lock_datetime
        except Lock.DoesNotExist:
            return self.week.lock_datetime

    def __str__(self):
        return f"{self.player} - {self.week} - {self.team}"

    class Meta:
        models.UniqueConstraint(fields=["player", "week"], name="unique_pick")
        indexes = [models.Index(fields=["player", "week"])]


class Board(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    player_status = models.ForeignKey(PlayerStatus, on_delete=models.DO_NOTHING)
    ranking = models.PositiveSmallIntegerField()

    pick_01 = models.CharField(max_length=3, null=True)
    pick_02 = models.CharField(max_length=3, null=True)
    pick_03 = models.CharField(max_length=3, null=True)
    pick_04 = models.CharField(max_length=3, null=True)
    pick_05 = models.CharField(max_length=3, null=True)
    pick_06 = models.CharField(max_length=3, null=True)
    pick_07 = models.CharField(max_length=3, null=True)
    pick_08 = models.CharField(max_length=3, null=True)
    pick_09 = models.CharField(max_length=3, null=True)
    pick_10 = models.CharField(max_length=3, null=True)
    pick_11 = models.CharField(max_length=3, null=True)
    pick_12 = models.CharField(max_length=3, null=True)
    pick_13 = models.CharField(max_length=3, null=True)
    pick_14 = models.CharField(max_length=3, null=True)
    pick_15 = models.CharField(max_length=3, null=True)
    pick_16 = models.CharField(max_length=3, null=True)
    pick_17 = models.CharField(max_length=3, null=True)
    pick_18 = models.CharField(max_length=3, null=True)

    result_01 = models.CharField(max_length=1, null=True)
    result_02 = models.CharField(max_length=1, null=True)
    result_03 = models.CharField(max_length=1, null=True)
    result_04 = models.CharField(max_length=1, null=True)
    result_05 = models.CharField(max_length=1, null=True)
    result_06 = models.CharField(max_length=1, null=True)
    result_07 = models.CharField(max_length=1, null=True)
    result_08 = models.CharField(max_length=1, null=True)
    result_09 = models.CharField(max_length=1, null=True)
    result_10 = models.CharField(max_length=1, null=True)
    result_11 = models.CharField(max_length=1, null=True)
    result_12 = models.CharField(max_length=1, null=True)
    result_13 = models.CharField(max_length=1, null=True)
    result_14 = models.CharField(max_length=1, null=True)
    result_15 = models.CharField(max_length=1, null=True)
    result_16 = models.CharField(max_length=1, null=True)
    result_17 = models.CharField(max_length=1, null=True)
    result_18 = models.CharField(max_length=1, null=True)


class EmailLogRecord(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=128)
    email = models.CharField(max_length=128)
