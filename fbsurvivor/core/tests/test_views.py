import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from fbsurvivor.core.models import MagicLink, Pick, PlayerStatus, Week


@pytest.fixture
def magic_link(players):
    _magic_link, token = MagicLink.issue(players[0].user)
    return token


@pytest.fixture
def year(seasons):
    return seasons[1].year


@pytest.fixture
def staff_client(client, db):
    user = User.objects.create(username="staffer", email="staffer@fbsurvivor.com", is_staff=True)
    client.force_login(user)
    return client


class TestLoginView:
    def test_get_does_not_consume_token(self, client, magic_link):
        # A GET (e.g. an email scanner prefetch) must show the confirmation
        # page without logging in or consuming the single-use token.
        response = client.get(reverse("enter", args=[magic_link]))

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session
        assert not MagicLink.from_token(magic_link).has_been_used

    def test_post_consumes_token_and_logs_in(self, client, magic_link):
        response = client.post(reverse("enter", args=[magic_link]))

        assert response.status_code == 302
        assert "_auth_user_id" in client.session
        assert MagicLink.from_token(magic_link).has_been_used

    def test_post_with_used_token_errors(self, client, magic_link):
        client.post(reverse("enter", args=[magic_link]))
        client.logout()

        response = client.post(reverse("enter", args=[magic_link]))

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session


class TestBoardView:
    def test_board_renders_for_unpaid_player(self, client, magic_link, year):
        # Regression: the player-* templates were unreachable because
        # templates/player was missing from TEMPLATES["DIRS"], so the
        # unpaid-player board flow raised TemplateDoesNotExist (500).
        client.post(reverse("enter", args=[magic_link]))

        response = client.get(reverse("board", args=[year]))

        assert response.status_code == 200


class TestPickViews:
    def test_view_picks(self, client, magic_link, year):
        client.post(reverse("enter", args=[magic_link]))
        url = reverse("picks", args=[year])
        response = client.get(url)
        assert response.status_code == 200

    def test_view_pick_week_is_locked(self, client, magic_link, year):
        client.post(reverse("enter", args=[magic_link]))
        url = reverse("pick", args=[year, 1])
        response = client.get(url, follow=True)
        assert response.status_code == 200

    def test_view_pick_get(self, client, magic_link, year):
        client.post(reverse("enter", args=[magic_link]))
        url = reverse("pick", args=[year, 5])
        response = client.get(url)
        assert response.status_code == 200

    def test_view_pick_post(self, client, magic_link, year, players):
        client.post(reverse("enter", args=[magic_link]))
        p1 = players[0]

        url = reverse("pick", args=[year, 5])
        response = client.post(url, {"team": "BUF"}, follow=True)
        pick = Pick.objects.get(player=p1, week__season__year=year, week__week_num=5)

        assert response.status_code == 200
        assert pick.team is not None
        assert pick.team.team_code == "BUF"

    def test_view_pick_post_bad_team(self, client, magic_link, year, players):
        client.post(reverse("enter", args=[magic_link]))
        url = reverse("pick", args=[year, 5])
        response = client.post(url, {"team": "WAS"}, follow=True)

        assert response.status_code == 200


class TestResultView:
    def test_loss_eliminates_picker_only(self, staff_client, year, players):
        # In conftest, players[0] picks "NE" and players[1] picks "BUF" in week 1.
        week = Week.objects.get(season__year=year, week_num=1)
        pick = Pick.objects.get(player=players[0], week=week)
        team_code = pick.team.team_code if pick.team else None

        url = reverse("result", args=[year, 1, team_code, "L"])
        response = staff_client.post(url)
        assert response.status_code == 302

        pick.refresh_from_db()
        assert pick.result == "L"

        # the player who picked the losing team is eliminated
        loser = PlayerStatus.objects.get(player=players[0], season__year=year)
        assert loser.is_survivor is False

        # a player who picked a different team is untouched
        survivor = PlayerStatus.objects.get(player=players[1], season__year=year)
        assert survivor.is_survivor is True

    def test_invalid_outcome_is_rejected(self, staff_client, year, players):
        week = Week.objects.get(season__year=year, week_num=1)
        pick = Pick.objects.get(player=players[0], week=week)
        team_code = pick.team.team_code if pick.team else None

        url = reverse("result", args=[year, 1, team_code, "X"])
        response = staff_client.post(url)
        assert response.status_code == 404
