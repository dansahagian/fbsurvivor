import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from fbsurvivor.core.models import EmailLogRecord, Pick, PlayerStatus, Week
from fbsurvivor.core.utils.authentication import CODE_SEND_MAX


@pytest.fixture
def code(monkeypatch):
    """Pin the emailed code so tests can submit it."""
    monkeypatch.setattr("fbsurvivor.core.views.accounts.generate_code", lambda: "123456")
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
    return client.post(reverse("index"), {"identifier": email})


class TestLoginView:
    def test_correct_code_logs_in_and_clears_pending_state(self, client, players, code):
        request_code(client, players[0].user.email)

        response = client.post(reverse("login"), {"code": code})

        assert response.status_code == 302
        assert "_auth_user_id" in client.session
        for key in ("identifier", "code_hash", "code_id", "code_expires_at", "user_id"):
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

    def test_username_gets_a_code_at_their_email(self, client, players, code):
        user = players[0].user

        response = request_code(client, user.username)

        assert EmailLogRecord.objects.filter(email=user.email).count() == 1
        assert user.email not in client.get(response.url).content.decode()
        assert client.post(reverse("login"), {"code": code}).status_code == 302

    def test_unknown_username_is_not_emailed(self, client, db):
        request_code(client, "nobody")

        assert EmailLogRecord.objects.count() == 0

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
        assert 'id="id_code_error"' in response.content.decode()
        # All three tries are still there: two misses, then the right code.
        client.post(reverse("login"), {"code": "000000"})
        client.post(reverse("login"), {"code": "000000"})
        assert client.post(reverse("login"), {"code": code}).status_code == 302

    def test_wrong_code_burns_a_try(self, client, players, code):
        request_code(client, players[0].user.email)

        response = client.post(reverse("login"), {"code": "000000"})

        assert response.status_code == 200
        assert response.context["tries"] == 2
        assert "_auth_user_id" not in client.session

    def test_three_wrong_codes_discard_the_code(self, client, players, code):
        request_code(client, players[0].user.email)

        for _ in range(3):
            client.post(reverse("login"), {"code": "000000"})

        assert "code_hash" not in client.session
        assert client.post(reverse("login"), {"code": code}).status_code == 200
        assert "_auth_user_id" not in client.session

    def test_replayed_session_cannot_reuse_tries(self, client, players, code):
        # Parallel requests all load the session before any saves it. Replaying the
        # pre-guess session stands in for that race: the tries must still be used up.
        request_code(client, players[0].user.email)
        pending = dict(client.session.items())

        for _ in range(3):
            client.post(reverse("login"), {"code": "000000"})

        session = client.session
        session.update(pending)
        session.save()

        response = client.post(reverse("login"), {"code": code})

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session

    def test_new_request_drops_the_earlier_account(self, client, players):
        request_code(client, players[0].user.email)

        request_code(client, "nobody@example.com")

        assert "user_id" not in client.session

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


class TestCodeSendLimit:
    def test_limit_stops_sending_codes(self, client, players):
        email = players[0].user.email
        for _ in range(CODE_SEND_MAX):
            assert request_code(client, email).status_code == 302

        response = request_code(client, email)

        assert response.status_code == 200
        assert "Too many login codes requested" in response.content.decode()
        assert EmailLogRecord.objects.count() == CODE_SEND_MAX

    def test_limit_survives_a_new_session(self, client, players):
        email = players[0].user.email
        for _ in range(CODE_SEND_MAX):
            request_code(client, email)
        client.cookies.clear()

        assert request_code(client, email).status_code == 200

    def test_email_and_username_share_one_limit(self, client, players):
        user = players[0].user
        for _ in range(CODE_SEND_MAX):
            request_code(client, user.email)

        assert request_code(client, user.username.upper()).status_code == 200

    def test_unknown_account_hits_the_same_limit(self, client, db):
        # Otherwise the limit message would reveal which accounts exist.
        for _ in range(CODE_SEND_MAX):
            request_code(client, "nobody@example.com")

        response = request_code(client, "nobody@example.com")

        assert "Too many login codes requested" in response.content.decode()

    def test_limit_is_per_account(self, client, players):
        for _ in range(CODE_SEND_MAX):
            request_code(client, players[0].user.email)

        assert request_code(client, players[1].user.email).status_code == 302

    def test_password_login_still_works_when_limited(self, client, password_user):
        for _ in range(CODE_SEND_MAX):
            request_code(client, password_user.email)

        assert password_login(client, password_user.email, PASSWORD).status_code == 302


PASSWORD = "correct-horse-battery"


@pytest.fixture(autouse=True)
def clear_cache():
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def password_user(players):
    user = players[0].user
    user.set_password(PASSWORD)
    user.save()
    return user


def password_login(client, email, password):
    return client.post(reverse("index"), {"identifier": email, "password": password})


class TestPasswordLogin:
    def test_correct_password_logs_in(self, client, password_user):
        response = password_login(client, password_user.email, PASSWORD)

        assert response.status_code == 302
        assert response.url == reverse("board_redirect")
        assert "_auth_user_id" in client.session
        assert EmailLogRecord.objects.count() == 0

    def test_wrong_password_is_rejected(self, client, password_user):
        response = password_login(client, password_user.email, "nope")

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session
        assert "Incorrect login or password" in response.content.decode()

    def test_unknown_account_looks_like_wrong_password(self, client, db):
        response = password_login(client, "nobody@example.com", "nope")

        assert response.status_code == 200
        assert "Incorrect login or password" in response.content.decode()

    def test_user_without_password_cannot_log_in_with_one(self, client, players):
        response = password_login(client, players[0].user.email, "")

        # A blank password falls through to the code flow instead.
        assert response.status_code == 302
        assert response.url == reverse("login")
        assert "_auth_user_id" not in client.session

    def test_lockout_after_repeated_failures(self, client, password_user):
        for _ in range(5):
            password_login(client, password_user.email, "nope")

        response = password_login(client, password_user.email, PASSWORD)

        assert response.status_code == 200
        assert "_auth_user_id" not in client.session
        assert "Too many attempts" in response.content.decode()

    def test_lockout_survives_a_new_session(self, client, password_user):
        for _ in range(5):
            password_login(client, password_user.email, "nope")
        client.cookies.clear()

        response = password_login(client, password_user.email.upper(), PASSWORD)

        assert "_auth_user_id" not in client.session
        assert "Too many attempts" in response.content.decode()

    def test_code_login_still_works_when_locked_out(self, client, password_user, code):
        for _ in range(5):
            password_login(client, password_user.email, "nope")

        request_code(client, password_user.email)

        assert client.post(reverse("login"), {"code": code}).status_code == 302

    def test_username_logs_in_ignoring_case(self, client, password_user):
        response = password_login(client, password_user.username.upper(), PASSWORD)

        assert response.status_code == 302
        assert client.session["_auth_user_id"] == str(password_user.pk)

    def test_email_logs_in_ignoring_case(self, client, password_user):
        response = password_login(client, password_user.email.upper(), PASSWORD)

        assert response.status_code == 302

    def test_email_and_username_share_one_lockout(self, client, password_user):
        for i in range(5):
            ident = password_user.email if i % 2 else password_user.username
            password_login(client, ident, "nope")

        response = password_login(client, password_user.username, PASSWORD)

        assert "_auth_user_id" not in client.session
        assert "Too many attempts" in response.content.decode()

    def test_index_has_password_manager_hints(self, client, db):
        body = client.get(reverse("index")).content.decode()

        assert 'autocomplete="username"' in body
        assert 'autocomplete="current-password"' in body


class TestSetPassword:
    def test_requires_login(self, client, db):
        response = client.get(reverse("set_password"))

        assert response.status_code == 302

    def test_sets_password_and_stays_logged_in(self, player_client, players):
        response = player_client.post(
            reverse("set_password"),
            {"new_password1": PASSWORD, "new_password2": PASSWORD},
        )

        assert response.status_code == 200
        players[0].user.refresh_from_db()
        assert players[0].user.check_password(PASSWORD)
        assert "_auth_user_id" in player_client.session
        assert player_client.get(reverse("set_password")).status_code == 200
        assert EmailLogRecord.objects.filter(email=players[0].user.email).count() == 1

    @pytest.mark.parametrize("dark", [True, False])
    def test_uses_player_theme(self, player_client, players, dark):
        players[0].is_dark_mode = dark
        players[0].save()

        body = player_client.get(reverse("set_password")).content.decode()

        assert ("css/dark.css" in body) is dark
        assert ("css/light.css" in body) is not dark

    def test_shows_password_rules_up_front(self, player_client):
        body = player_client.get(reverse("set_password")).content.decode()

        assert "at least 8 characters" in body
        assert "commonly used password" in body
        assert 'placeholder="new password"' in body
        assert 'placeholder="confirm new password"' in body

    def test_works_for_staff_without_a_player(self, staff_client):
        assert staff_client.get(reverse("set_password")).status_code == 200

    def test_rejects_mismatched_passwords(self, player_client, players):
        response = player_client.post(
            reverse("set_password"),
            {"new_password1": PASSWORD, "new_password2": PASSWORD + "x"},
        )

        assert response.status_code == 200
        players[0].user.refresh_from_db()
        assert not players[0].user.check_password(PASSWORD)

    def test_rejects_weak_password(self, player_client, players):
        response = player_client.post(
            reverse("set_password"),
            {"new_password1": "password", "new_password2": "password"},
        )

        assert response.status_code == 200
        players[0].user.refresh_from_db()
        assert not players[0].user.check_password("password")


class TestPasswordLabel:
    def test_board_says_set_without_a_password(self, player_client, year):
        body = player_client.get(reverse("board", args=[year])).content.decode()

        assert "set password" in body
        assert "change password" not in body

    def test_board_says_change_with_a_password(self, client, password_user, year):
        client.force_login(password_user)

        body = client.get(reverse("board", args=[year])).content.decode()

        assert "change password" in body

    def test_page_says_change_with_a_password(self, client, password_user):
        client.force_login(password_user)

        body = client.get(reverse("set_password")).content.decode()

        assert "Change the password" in body


class TestCreatePlayer:
    def test_creates_player(self, staff_client):
        response = staff_client.post(
            reverse("create_player"), {"username": "newbie", "email": "newbie@example.com"}
        )

        assert response.status_code == 200
        assert User.objects.filter(username="newbie").exists()

    def test_rejects_at_in_username(self, staff_client):
        response = staff_client.post(
            reverse("create_player"), {"username": "dan@home", "email": "dan@example.com"}
        )

        assert response.status_code == 200
        assert "contain @" in response.content.decode()
        assert not User.objects.filter(email="dan@example.com").exists()

    def test_invalid_form_rerenders_instead_of_erroring(self, staff_client):
        response = staff_client.post(
            reverse("create_player"), {"username": "newbie", "email": "not-an-email"}
        )

        assert response.status_code == 200
        assert not User.objects.filter(username="newbie").exists()


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
