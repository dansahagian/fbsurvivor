from django.urls import path

from fbsurvivor.core.views import (
    assume,
    board,
    board_redirect,
    buy_back,
    decline_buy_back,
    enter,
    get_players,
    login,
    logout,
    manager,
    paid,
    payouts,
    pick,
    picks,
    play,
    result,
    results,
    rules,
    seasons,
    theme,
    update_reminders,
    user_paid,
)

urlpatterns = [
    path("", login, name="login"),  # pyright: ignore
    path("logout", logout, name="logout"),
    path("enter/<str:magic_link_id>/", enter, name="enter"),
    path("assume/<str:username>/", assume, name="assume"),
    path("board/", board_redirect, name="board_redirect"),
    path("board/<int:year>/", board, name="board"),
    path("play/<int:year>/", play, name="play"),  # pyright: ignore
    path("buy-back/<int:year>/", buy_back, name="buy_back"),
    path("decline-buy-back/<int:year>/", decline_buy_back, name="decline_buy_back"),
    path("payouts/", payouts, name="payouts"),
    path("rules/", rules, name="rules"),
    path("seasons/", seasons, name="seasons"),
    path("theme/", theme, name="theme"),
    path("picks/<int:year>/", picks, name="picks"),
    path("picks/<int:year>/<int:week>/", pick, name="pick"),  # pyright: ignore
    path("manager/<int:year>/", manager, name="manager"),
    path("paid/<int:year>/", paid, name="paid"),
    path("paid/<int:year>/<str:username>/", user_paid, name="user_paid"),
    path("results/<int:year>/", results, name="results"),
    path("results/<int:year>/<int:week>/<str:team>/<str:outcome>/", result, name="result"),
    path("players/<int:year>", get_players, name="players"),
    path("reminders/<str:kind>/<str:status>/", update_reminders, name="update_reminders"),
]
