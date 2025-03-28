from django import forms

from fbsurvivor.core.models import Pick, Team


class EmailForm(forms.Form):
    email = forms.EmailField(label="email")


class PlayerForm(forms.Form):
    username = forms.CharField(label="username", max_length=20)
    email = forms.EmailField(label="email (won't be displayed)")


class PickForm(forms.Form):
    def __init__(self, player, season, week, *args, **kwargs):
        super().__init__(*args, **kwargs)

        picks = Pick.objects.filter(
            player=player, week__season=season, team__isnull=False
        ).values_list("team__team_code", flat=True)

        teams = (
            Team.objects.filter(season=season)
            .exclude(bye_week=week.week_num)
            .exclude(team_code__in=picks)
            .order_by("team_code")
        )

        choices = [("", "--")]
        choices.extend(
            [
                (team.team_code, f"{team.team_code} ({team.name})")
                for team in teams
                if not team.is_locked(week)
            ]
        )

        self.fields["team"] = forms.ChoiceField(choices=choices, required=False)


class MessageForm(forms.Form):
    subject = forms.CharField(label="subject", max_length=25)
    message = forms.CharField(label="message", widget=forms.Textarea)
