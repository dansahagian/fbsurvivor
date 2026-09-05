import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from fbsurvivor.core.models import EmailLogRecord, Pick, PlayerStatus, Week


@pytest.fixture
def code(monkeypatch):
    """Pin the emailed code so tests can submit it."""
    monkeypatch.setattr("fbsurvivor.core.views.generate_code", lambda: "123456")
    return "123456"


@pytest.fixture
def year(seasons):
    return seasons[1].year


@pytest.fixture
def player_client(client, players):
    client.force_login(players[0].user)
    return client


@pytest.fixture
def staff_client(client, db):
    user = User.objects.create(username="staffer", email="staffer@fbsurvivor.com", is_staff=True)
    client.force_login(user)
    return client


def request_code(client, email):
    return client.post(reverse("index"), {"email": email})


class TestLoginView:
    def test_correct_code_logs_in_and_clears_pending_state(self, client, players, code):
        request_code(client, players[0].user.email)

        response = client.post(reverse("login"), {"code": code})

        assert response.status_code == 302
        assert "_auth_user_id" in client.session
        for key in ("email", "code_hash", "code_tries", "code_expires_at", "user_id"):
            assert key not in client.session

    def test_unknown_email_behaves_like_a_wrong_code(self, client, db, code):
        # Regression: the unknown-email session has no user_id, and reading it
        # unconditionally 500'd -- which also leaked which addresses exist.
        request_code(client, "nobody@example.com")

        response = client.post(reverse("login"), {"code": code})

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_unknown_email_is_not_emailed(self, client, db):
        request_code(client, "nobody@example.com")

        assert EmailLogRecord.objects.count() == 0

    def test_known_email_is_emailed(self, client, players):
        request_code(client, players[0].user.email)

        assert EmailLogRecord.objects.count() == 1

    def test_padded_code_is_accepted(self, client, players, code):
        request_code(client, players[0].user.email)

        response = client.post(reverse("login"), {"code": f"  {code}  "})

        assert response.status_code == 302

    @pytest.mark.parametrize("bad_code", ["", "12345", "1234567"])
    def test_wrong_length_does_not_burn_a_try(self, client, players, code, bad_code):
        # A malformed entry can never be the right code, so it costs a message,
        # not the pending login.
        request_code(client, players[0].user.email)

        response = client.post(reverse("login"), {"code": bad_code})

        assert response.status_code == 200
        assert client.session["code_tries"] == 0
        assert 'id="id_code_error"' in response.content.decode()
        assert client.post(reverse("login"), {"code": code}).status_code == 302

    def test_wrong_code_burns_a_try(self, client, players, code):
        request_code(client, players[0].user.email)

        response = client.post(reverse("login"), {"code": "000000"})

        assert response.status_code == 200
        assert client.session["code_tries"] == 1
        assert "_auth_user_id" not in client.session

    def test_three_wrong_codes_discard_the_code(self, client, players, code):
        request_code(client, players[0].user.email)

        for _ in range(3):
            client.post(reverse("login"), {"code": "000000"})

        assert "code_hash" not in client.session
        assert client.post(reverse("login"), {"code": code}).status_code == 200
        assert "_auth_user_id" not in client.session

    def test_expired_code_is_rejected(self, client, players, code):
        request_code(client, players[0].user.email)
        session = client.session
        session["code_expires_at"] = "2020-01-01T00:00:00+00:00"
        session.save()

        response = client.post(reverse("login"), {"code": code})

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session
        assert "code_hash" not in client.session

    def test_login_page_without_a_pending_code_redirects(self, client, db):
        response = client.get(reverse("login"))

        assert response.status_code == 302

    def test_code_input_supports_autofill(self, client, players, code):
        request_code(client, players[0].user.email)

        body = client.get(reverse("login")).content.decode()

        assert 'autocomplete="one-time-code"' in body
        assert 'inputmode="numeric"' in body
        assert 'minlength="6"' in body
        assert 'maxlength="6"' in body


class TestBoardView:
    def test_board_renders_for_unpaid_player(self, player_client, year):
        # Regression: the player-* templates were unreachable because
        # templates/player was missing from TEMPLATES["DIRS"], so the
        # unpaid-player board flow raised TemplateDoesNotExist (500).
        response = player_client.get(reverse("board", args=[year]))

        assert response.status_code == 200


class TestPickViews:
    def test_view_picks(self, player_client, year):
        url = reverse("picks", args=[year])
        response = player_client.get(url)
        assert response.status_code == 200

    def test_view_pick_week_is_locked(self, player_client, year):
        url = reverse("pick", args=[year, 1])
        response = player_client.get(url, follow=True)
        assert response.status_code == 200

    def test_view_pick_get(self, player_client, year):
        url = reverse("pick", args=[year, 5])
        response = player_client.get(url)
        assert response.status_code == 200

    def test_view_pick_post(self, player_client, year, players):
        p1 = players[0]

        url = reverse("pick", args=[year, 5])
        response = player_client.post(url, {"team": "BUF"}, follow=True)
        pick = Pick.objects.get(player=p1, week__season__year=year, week__week_num=5)

        assert response.status_code == 200
        assert pick.team is not None
        assert pick.team.team_code == "BUF"

    def test_view_pick_post_bad_team(self, player_client, year):
        url = reverse("pick", args=[year, 5])
        response = player_client.post(url, {"team": "WAS"}, follow=True)

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
