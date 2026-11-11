from django import forms

from fbsurvivor.core.models import Pick, Team


class SignInForm(forms.Form):
    identifier = forms.CharField(
        label="email or username",
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "placeholder": "email or username",
            }
        ),
    )
    password = forms.CharField(
        label="password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password", "placeholder": "password (optional)"}
        ),
    )


class CodeForm(forms.Form):
    code = forms.CharField(
        label="code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )


class PlayerForm(forms.Form):
    username = forms.CharField(label="username", max_length=20)
    email = forms.EmailField(label="email")

    def clean_username(self):
        username = self.cleaned_data["username"]
        # Sign-in treats anything with an @ as an email, so this player could never use it.
        if "@" in username:
            raise forms.ValidationError("Usernames can't contain @.")
        return username


class PickForm(forms.Form):
    def __init__(self, player, season, week, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get current pick for this week if it exists
        current_pick = Pick.objects.filter(player=player, week=week, team__isnull=False).first()
        initial_team = current_pick.team.team_code if current_pick and current_pick.team else ""

        # Get all teams this player has picked in this season
        picks = Pick.objects.filter(
            player=player, week__season=season, team__isnull=False
        ).values_list("team__team_code", flat=True)

        # If we have a current pick for this week, exclude it from the picks to exclude
        if current_pick and current_pick.team:
            picks = [p for p in picks if p != current_pick.team.team_code]

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

        self.fields["team"] = forms.ChoiceField(
            choices=choices,
            required=False,
            initial=initial_team,
        )
