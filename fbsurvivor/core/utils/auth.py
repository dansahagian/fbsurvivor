import secrets
from datetime import timedelta

import sentry_sdk
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from jwt import ExpiredSignatureError, InvalidSignatureError, decode, encode
from jwt.exceptions import DecodeError
from typing_extensions import Tuple

from fbsurvivor.core.models import LoggedOutTokens, MagicLink, Player, Season
from fbsurvivor.core.utils.emails import send_email
from fbsurvivor.settings import DOMAIN, SECRET_KEY


def create_token(player: Player) -> str:
    exp = timezone.now() + timedelta(days=30)
    payload = {"username": player.username, "exp": exp}

    token = encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_token(token: str) -> Player | None:
    try:
        LoggedOutTokens.objects.get(id=token)
        return None
    except LoggedOutTokens.DoesNotExist:
        try:
            payload = decode(token, SECRET_KEY, algorithms="HS256")
            username = payload.get("username")
            return Player.objects.get(username=username)
        except (ExpiredSignatureError, InvalidSignatureError, Player.DoesNotExist, DecodeError):
            return None


def authenticate_player(view):
    def inner(*args, **kwargs):
        request = args[0]
        if player := get_authenticated_player(request):
            sentry_sdk.set_user({"username": player.username})
            kwargs["player"] = player
            kwargs["path"] = request.session.get("path")
            request.session["path"] = request.path
            return view(*args, **kwargs)
        request.session.delete("token")

        return redirect(reverse("login"))

    return inner


def authenticate_admin(view):
    def inner(*args, **kwargs):
        request = args[0]
        if player := get_authenticated_admin(request):
            sentry_sdk.set_user({"username": player.username})
            kwargs["player"] = player
            kwargs["path"] = request.session.get("path")
            request.session["path"] = request.path
            return view(*args, **kwargs)
        request.session.delete("token")

        return redirect(reverse("login"))

    return inner


def get_authenticated_player(request) -> Player | None:
    token = request.session.get("token")

    if not token:
        return None

    return verify_token(token)


def get_authenticated_admin(request) -> Player | None:
    player = get_authenticated_player(request)
    return player if player and player.is_admin else None


def get_season_context(year: int, **kwargs) -> Tuple[Season, dict]:
    season = get_object_or_404(Season, year=year)
    return season, {
        "season": season,
        "player": kwargs["player"],
    }


def send_magic_link(player: Player) -> None:
    magic_link = MagicLink.objects.create(id=secrets.token_urlsafe(32), player=player)

    subject = "Survivor Login"
    link = f"{DOMAIN}/enter/{magic_link.id}"
    message = f"Click the link below to login. It expires in 30 minutes.\n\n{link}"

    send_email(subject, [player.email], message)
