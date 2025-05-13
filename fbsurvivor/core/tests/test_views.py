import secrets

import pytest
from django.urls import reverse

from fbsurvivor.core.models import MagicLink, Pick
from fbsurvivor.core.utils.helpers import get_player_context


@pytest.fixture
def magic_link(players):
    return MagicLink.objects.create(id=secrets.token_urlsafe(32), player=players[0])


@pytest.fixture
def year(seasons):
    return seasons[1].year


def test_get_player_info_and_context(players, seasons, year, player_statuses):
    p1 = players[0]

    season, player_status, context = get_player_context(p1, year)
    assert season == seasons[1]
    assert player_status == player_statuses["p1"][1]
    assert "player" in context
    assert "season" in context
    assert "player_status" in context


class TestPickViews:
    def test_view_picks(self, client, magic_link, year):
        client.get(reverse("enter", args=[magic_link.id]))
        url = reverse("picks", args=[year])
        response = client.get(url)
        assert response.status_code == 200

    def test_view_pick_week_is_locked(self, client, magic_link, year):
        client.get(reverse("enter", args=[magic_link.id]))
        url = reverse("pick", args=[year, 1])
        response = client.get(url, follow=True)
        assert response.status_code == 200

    def test_view_pick_get(self, client, magic_link, year):
        client.get(reverse("enter", args=[magic_link.id]))
        url = reverse("pick", args=[year, 5])
        response = client.get(url)
        assert response.status_code == 200

    def test_view_pick_post(self, client, magic_link, year, players):
        client.get(reverse("enter", args=[magic_link.id]))
        p1 = players[0]

        url = reverse("pick", args=[year, 5])
        response = client.post(url, {"team": "BUF"}, follow=True)
        pick = Pick.objects.get(player=p1, week__season__year=year, week__week_num=5)

        assert response.status_code == 200
        assert pick.team.team_code == "BUF"  # pyright: ignore

    def test_view_pick_post_bad_team(self, client, magic_link, year, players):
        client.get(reverse("enter", args=[magic_link.id]))
        url = reverse("pick", args=[year, 5])
        response = client.post(url, {"team": "WAS"}, follow=True)

        assert response.status_code == 200
