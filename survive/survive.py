import os
from functools import wraps

from flask import abort
from flask import Blueprint
from flask import Flask
from flask import flash
from flask import redirect
from flask import request
from flask import render_template
from flask import send_from_directory

from survive.db import *
from survive.settings import *
from survive.tasks import send_email

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG

bp = Blueprint("survive", __name__, template_folder="templates/")


def validate_link(func):
    @wraps(func)
    def wrapper(**kwargs):
        if valid_link(kwargs["link"]):
            return func(**kwargs)
        return abort(404)

    return wrapper


def validate_year(func):
    @wraps(func)
    def wrapper(**kwargs):
        if valid_year(kwargs["year"]):
            return func(**kwargs)
        return abort(404)

    return wrapper


def validate_week(func):
    @wraps(func)
    def wrapper(**kwargs):
        if valid_week(kwargs["week"]):
            return func(**kwargs)
        return abort(404)

    return wrapper


def validate_email(func):
    @wraps(func)
    def wrapper(**kwargs):
        if email_confirmed(kwargs["link"]):
            return func(**kwargs)
        return render_template("not-confirmed.html")

    return wrapper


def validate_admin(func):
    @wraps(func)
    def wrapper(**kwargs):
        if is_admin(kwargs["link"]):
            return func(**kwargs)
        return abort(404)

    return wrapper


@bp.route("/", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"].lower()

        if len(str(username)) > 20:
            flash("Username is greater than 20 characters! Choose again.")
            return redirect("/")

        if username_available(username):
            link = add_user(username, email)
            confirm_link = f"{ROOT_URL}/{link}/confirm"
            subject = "Confirm your Email - Football Survivor"
            message = f"Confirm your email address by clicking the link below:\n{confirm_link}"

            send_email(subject, [email], message)
            return render_template("email.html")

        flash("Username already exists! Pick another!")
        return redirect("/")


@bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return render_template("forgot.html")

    if request.method == "POST":
        email = request.form["email"].lower()

        links = get_links_from_email(email)
        if links:
            subject = "Survivor Links"
            message = (
                "We found the following links associated with your email address:\n\n"
            )
            for link in links:
                message += f"{ROOT_URL}/{link}\n\n"

            send_email(subject, [email], message)
        return render_template("forgot-sent.html")


@bp.route("/<link>/confirm", methods=["GET"])
@validate_link
def confirm(link):
    year = get_current_year()
    email = get_email(link)
    if email_confirmed(link):
        return redirect(f"/{link}/{year}")

    confirm_email(link)

    user_link = f"{ROOT_URL}/{link}"
    subject = "Football Survivor Link"
    message = f"Use this link to make your picks and check the board:\n{user_link}"

    send_email(subject, [email], message)

    flash("Email Confirmed! Bookmark this page or check your email for your link.")
    return redirect(f"/{link}/{year}")


@bp.route("/<link>", methods=["GET"])
@validate_link
@validate_email
def dash(link):
    year = get_current_year()
    return redirect(f"/{link}/{year}")


@bp.route("/<link>/<year>", methods=["GET"])
@validate_link
@validate_email
@validate_year
def user(link, year):
    admin = is_admin(link)
    retired = user_retired(link, year)
    if retired:
        flash("Reminder: You retired!")
    username = get_username(link)
    data = get_board(year)
    years = get_years()
    play = user_playing(link, year)
    retire = (not retired) and (int(year) == get_current_year()) and play
    if play and not is_paid(link, year):
        flash("Unpaid! Venmo $30 to @dansah or email picks@fbsurvivor.com.")
    return render_template(
        "user.html",
        years=years,
        link=link,
        data=data,
        username=username,
        year=year,
        play=play,
        retire=retire,
        admin=admin,
    )


@bp.route("/<link>/<year>/paid", methods=["GET"])
@validate_link
@validate_admin
def admin_paid(link, year):
    year = int(year)
    statuses = get_paid_statuses(year)
    return render_template("paid.html", link=link, year=year, statuses=statuses)


@bp.route("/<link>/<year>/paid/<username>", methods=["GET"])
@validate_link
@validate_admin
def admin_paid_update(link, year, username):
    year = int(year)
    update_paid_status(year, username)
    flash(f"{username} marked as PAID!")
    return redirect(f"/{link}/{year}/paid")


@bp.route("/<link>/<year>/picks", methods=["GET"])
@validate_link
@validate_email
@validate_year
def picks(link, year):
    username = get_username(link)
    user_picks = get_user_picks(link, year)
    lock = year_locked(year)
    wins = len([x[2] for x in user_picks if x[2] == "W"])
    loss = len([x[2] for x in user_picks if x[2] == "L"])
    return render_template(
        "picks.html",
        username=username,
        link=link,
        year=year,
        lock=lock,
        picks=user_picks,
        ws=wins,
        ls=loss,
    )


@bp.route("/<link>/<year>/picks/<week>", methods=["GET", "POST"])
@validate_link
@validate_email
@validate_year
@validate_week
def pick(link, year, week):
    teams = get_team_choices(link, year, week)

    if request.method == "GET":
        if week_locked(year, week):
            flash(f"Week {week} is locked! Cannot Edit!")
            return redirect(f"/{link}/{year}/picks")
        user_pick = get_current_pick(link, year, week)
        return render_template(
            "pick.html", link=link, year=year, week=int(week), pick=user_pick, c=teams
        )

    if request.method == "POST":
        user_picks = [x[1] for x in get_user_picks(link, year)]
        user_pick = request.form["pick"]

        if user_pick in teams:
            if user_pick in user_picks and user_pick != "--":
                flash(f"Pick NOT updated! {user_pick} already used.")
            else:
                update_pick(link, year, week, user_pick)
                flash(f"Pick updated! Week {week}: {user_pick}")

                return redirect(f"/{link}/{year}/picks")
        flash(f"{user_pick} is not a valid choice!")
        return redirect(f"/{link}/{year}/picks")


@bp.route("/<link>/<year>/play", methods=["GET", "POST"])
@validate_link
@validate_email
@validate_year
def play_year(link, year):
    if year_locked(year):
        flash(f"{year} is locked! Come back next year!")
        return redirect(f"/{link}/{year}")
    elif user_playing(link, year):
        flash(f"You are already playing for {year}!")
        return redirect(f"/{link}/{year}")

    if request.method == "GET":
        return render_template("rules.html", confirm_link=f"/{link}/{year}/play")

    if request.method == "POST":
        add_user_picks(link, year)
        add_paid_status(link, year)
        flash(f"You are playing in the {year} league. Good luck!")
        return redirect(f"/{link}/{year}")


@bp.route("/<link>/<year>/retire", methods=["GET"])
@validate_link
@validate_email
@validate_year
def retire_year(link, year):
    if user_playing(link, year) and int(year) == get_current_year():
        set_retired(link, year)
        flash("You retired! See you next year!")
        return redirect(f"/{link}/{year}")

    flash("You can not retire since you are not playing!")
    return redirect(f"/{link}/{year}")


@bp.route("/favicon.ico")
def favicon():
    root = os.path.join(bp.root_path, "static")
    return send_from_directory(root, "favicon.ico")


@bp.route("/css/main.css")
def css():
    root = os.path.join(bp.root_path, "static/css")
    return send_from_directory(root, "main.css")


@bp.route("/fonts/OpenSans-Regular.eot")
def font_eot():
    root = os.path.join(bp.root_path, "static/fonts")
    return send_from_directory(root, "OpenSans-Regular.eot")


@bp.route("/fonts/OpenSans-Regular.ttf")
def font_ttf():
    root = os.path.join(bp.root_path, "static/fonts")
    return send_from_directory(root, "OpenSans-Regular.ttf")


@bp.errorhandler(404)
def page_not_found(error):
    print(error)
    return render_template("404.html"), 404
