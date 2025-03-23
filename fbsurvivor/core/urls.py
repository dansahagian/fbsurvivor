from django.urls import path

from fbsurvivor.core.views import (
    assume,
    board,
    board_redirect,
    enter,
    get_players,
    login,
    logout,
    manager,
    more,
    paid,
    payouts,
    pick,
    picks,
    play,
    remind,
    reminders,
    result,
    results,
    retire,
    rules,
    seasons,
    send_message,
    send_message_all,
    theme,
    update_reminders,
    user_paid,
)

urlpatterns = [
    path("", login, name="login"),  # pyright: ignore
    path("logout", logout, name="logout"),
    path("enter/<str:token>/", enter, name="enter"),
    path("assume/<str:username>/", assume, name="assume"),
    path("board/", board_redirect, name="board_redirect"),
    path("board/<int:year>/", board, name="board"),
    path("play/<int:year>/", play, name="play"),  # pyright: ignore
    path("retire/<int:year>/", retire, name="retire"),
    path("more/", more, name="more"),
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
    path("remind/<int:year>/", remind, name="remind"),
    path("players/<int:year>", get_players, name="players"),
    path("message/<int:year>/", send_message, name="send_message"),  # pyright: ignore
    path("message-all/", send_message_all, name="send_message_all"),  # pyright: ignore
    path("reminders/", reminders, name="reminders"),
    path("reminders/<str:kind>/<str:status>/", update_reminders, name="update_reminders"),
]
