from django.urls import path

from fbsurvivor.core.views.accounts import (
    IndexView,
    LoginView,
    clean_session,
    logout_view,
    theme,
    update_reminders,
)
from fbsurvivor.core.views.board import board, board_redirect, buy_back, decline_buy_back, play
from fbsurvivor.core.views.manager import (
    assume_player,
    cache_season,
    create_player,
    get_players,
    manager,
    paid,
    paid_buyback,
    result,
    result_no_pick,
    results,
    user_paid,
    user_paid_buyback,
)
from fbsurvivor.core.views.pages import payouts, payouts_current, rules, seasons
from fbsurvivor.core.views.picks import pick, picks

urlpatterns = [
    path("", IndexView.as_view(), name="index"),
    path("login", LoginView.as_view(), name="login"),
    path("clean-session", clean_session, name="clean_session"),
    path("logout", logout_view, name="logout"),
    path("board", board_redirect, name="board_redirect"),
    path("board/<int:year>", board, name="board"),
    path("play/<int:year>", play, name="play"),
    path("buy-back/<int:year>", buy_back, name="buy_back"),
    path("decline-buy-back/<int:year>", decline_buy_back, name="decline_buy_back"),
    path("payouts", payouts, name="payouts"),
    path("payouts/current", payouts_current, name="payouts_current"),
    path("rules", rules, name="rules"),
    path("seasons", seasons, name="seasons"),
    path("theme", theme, name="theme"),
    path("picks/<int:year>", picks, name="picks"),
    path("picks/<int:year>/<int:week>", pick, name="pick"),
    path("manager/<int:year>", manager, name="manager"),
    path("create_player", create_player, name="create_player"),
    path("paid/<int:year>", paid, name="paid"),
    path("paid/<int:year>/<str:username>", user_paid, name="user_paid"),
    path("paid-buyback/<int:year>", paid_buyback, name="paid_buyback"),
    path("paid-buyback/<int:year>/<str:username>", user_paid_buyback, name="user_paid_buyback"),
    path("results/<int:year>", results, name="results"),
    path("results/<int:year>/<int:week>/<str:team>/<str:outcome>", result, name="result"),
    path("results/<int:year>/<int:week>/no-pick", result_no_pick, name="result_no_pick"),
    path("players/<int:year>", get_players, name="players"),
    path("assume/<str:username>", assume_player, name="assume_player"),
    path("reminders/<str:kind>/<str:status>", update_reminders, name="update_reminders"),
    path("cache_season/<int:year>", cache_season, name="cache_season"),
]
