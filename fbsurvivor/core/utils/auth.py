import hashlib

import arrow
import sentry_sdk
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from jwt import ExpiredSignatureError, InvalidSignatureError, decode, encode
from typing_extensions import Tuple

from fbsurvivor.core.models import Player, Season, TokenHash
from fbsurvivor.core.utils.emails import send_email
from fbsurvivor.settings import DOMAIN, SECRET_KEY


def get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_token(player: Player) -> str:
    exp = arrow.now().shift(days=30).datetime
    payload = {"username": player.username, "exp": exp}

    token = encode(payload, SECRET_KEY, algorithm="HS256")
    TokenHash.objects.create(hash=get_token_hash(token), player=player)
    return token


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


def check_token_and_get_player(payload, token) -> Player | None:
    username = payload.get("username")

    if not username:
        return None

    try:
        player = Player.objects.get(username=username)
    except Player.DoesNotExist:
        return None

    try:
        TokenHash.objects.get(player=player, hash=get_token_hash(token))
        return player
    except TokenHash.DoesNotExist:
        return None


def get_authenticated_player(request) -> Player | None:
    token = request.session.get("token")

    if not token:
        return None

    try:
        payload = decode(token, SECRET_KEY, algorithms="HS256")
        return check_token_and_get_player(payload, token)
    except (ExpiredSignatureError, InvalidSignatureError):
        return None


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
    token = create_token(player)
    subject = "Survivor Login"
    message = f"Click the link below to login\n\n{DOMAIN}/enter/{token}"
    send_email(subject, [player.email], message)
