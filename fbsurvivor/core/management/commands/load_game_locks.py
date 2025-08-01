from datetime import datetime

from django.core.management.base import BaseCommand

from fbsurvivor.core.models import Lock, Season, Team, Week


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("year", type=int)
        parser.add_argument("filename", type=str)

    def handle(self, *args, **options):
        year = options["year"]
        filename = options["filename"]

        n_created = 0
        n_updated = 0

        season = Season.objects.get(year=year)

        with open(filename, "r") as f:
            for line in f:
                week_num, team_code1, team_code2, lock_datetime = line.strip("/n").split(",")
                week = Week.objects.get(season=season, week_num=week_num)
                team1 = Team.objects.get(season=season, team_code=team_code1)
                team2 = Team.objects.get(season=season, team_code=team_code2)

                lock_datetime = datetime.fromisoformat(lock_datetime)

                _, created = Lock.objects.update_or_create(
                    week=week, team=team1, defaults={"lock_datetime": lock_datetime}
                )

                if created:
                    n_created += 1
                else:
                    n_updated += 1

                _, created = Lock.objects.update_or_create(
                    week=week, team=team2, defaults={"lock_datetime": lock_datetime}
                )

                if created:
                    n_created += 1
                else:
                    n_updated += 1

        print(f"Created: {n_created} and Updated: {n_updated} locks!")
