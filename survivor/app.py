import os

from flask import Flask, flash, redirect, request
from flask import render_template as rt
from flask import send_from_directory as sfd

from survivor import db
from survivor.tasks import send_email
from survivor.validators import (
    validate_admin, validate_email, validate_link, validate_week, validate_year
)

from survivor.settings import *

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG


@app.route("/", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return rt("signup.html")

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"].lower()

        if len(str(username)) > 20:
            flash("Username is greater than 20 characters! Choose again.")
            return redirect("/")

        if db.username_available(username):
            link = db.add_user(username, email)
            confirm_link = f"{ROOT_URL}/{link}/confirm"
            subject = "Confirm your Email - Football Survivor"
            message = f"Confirm your email address by clicking the link below:\n{confirm_link}"

            send_email(subject, [email], message)
            return rt("email.html")

        flash("Username already exists! Pick another!")
        return redirect("/")


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return rt("forgot.html")

    if request.method == "POST":
        email = request.form["email"].lower()

        links = db.get_links_from_email(email)
        if links:
            subject = "Survivor Links"
            message = (
                "We found the following links associated with your email address:\n\n"
            )
            for link in links:
                message += f"{ROOT_URL}/{link}\n\n"

            send_email(subject, [email], message)
        return rt("forgot-sent.html")


@app.route("/<link>/confirm", methods=["GET"])
@validate_link
def confirm(link):
    year = db.get_current_year()
    email = db.get_email(link)
    if db.email_confirmed(link):
        return redirect(f"/{link}/{year}")

    db.confirm_email(link)

    user_link = f"{ROOT_URL}/{link}"
    subject = "Football Survivor Link"
    message = f"Use this link to make your picks and check the board:\n{user_link}"

    send_email(subject, [email], message)

    flash("Email Confirmed! Bookmark this page or check your email for your link.")
    return redirect(f"/{link}/{year}")


@app.route("/<link>", methods=["GET"])
@validate_link
@validate_email
def dash(link):
    year = db.get_current_year()
    return redirect(f"/{link}/{year}")


@app.route("/<link>/<year>", methods=["GET"])
@validate_link
@validate_email
@validate_year
def user(link, year):
    is_admin = db.is_admin(link)
    retired = db.user_retired(link, year)
    if retired:
        flash("Reminder: You retired!")
    username = db.get_username(link)
    data = db.get_board(year)
    years = db.get_years()
    play = db.user_playing(link, year)
    retire = (not retired) and (int(year) == db.get_current_year()) and play
    if play and not db.is_paid(link, year):
        flash("Unpaid! Venmo $30 to @dansah or email picks@fbsurvivor.com.")
    return rt(
        "user.html",
        years=years,
        link=link,
        data=data,
        username=username,
        year=year,
        play=play,
        retire=retire,
        admin=is_admin,
    )


@app.route("/<link>/<year>/paid", methods=["GET"])
@validate_link
@validate_admin
def admin_paid(link, year):
    year = int(year)
    statuses = db.get_paid_statuses(year)
    return rt("paid.html", link=link, year=year, statuses=statuses)


@app.route("/<link>/<year>/paid/<username>", methods=["GET"])
@validate_link
@validate_admin
def admin_paid_update(link, year, username):
    year = int(year)
    db.update_paid_status(year, username)
    flash(f"{username} marked as PAID!")
    return redirect(f"/{link}/{year}/paid")


@app.route("/<link>/<year>/picks", methods=["GET"])
@validate_link
@validate_email
@validate_year
def picks(link, year):
    username = db.get_username(link)
    user_picks = db.get_user_picks(link, year)
    lock = db.year_locked(year)
    wins = len([x[2] for x in user_picks if x[2] == "W"])
    loss = len([x[2] for x in user_picks if x[2] == "L"])
    return rt(
        "picks.html",
        username=username,
        link=link,
        year=year,
        lock=lock,
        picks=user_picks,
        ws=wins,
        ls=loss,
    )


@app.route("/<link>/<year>/picks/<week>", methods=["GET", "POST"])
@validate_link
@validate_email
@validate_year
@validate_week
def pick(link, year, week):
    teams = db.get_team_choices(link, year, week)

    if request.method == "GET":
        if db.week_locked(year, week):
            flash(f"Week {week} is locked! Cannot Edit!")
            return redirect(f"/{link}/{year}/picks")
        user_pick = db.get_current_pick(link, year, week)
        return rt(
            "pick.html", link=link, year=year, week=int(week), pick=user_pick, c=teams
        )

    if request.method == "POST":
        user_picks = [x[1] for x in db.get_user_picks(link, year)]
        user_pick = request.form["pick"]

        if user_pick in teams:
            if user_pick in user_picks and user_pick != "--":
                flash(f"Pick NOT updated! {user_pick} already used.")
            else:
                db.update_pick(link, year, week, user_pick)
                flash(f"Pick updated! Week {week}: {user_pick}")

                return redirect(f"/{link}/{year}/picks")
        flash(f"{user_pick} is not a valid choice!")
        return redirect(f"/{link}/{year}/picks")


@app.route("/<link>/<year>/play", methods=["GET", "POST"])
@validate_link
@validate_email
@validate_year
def play_year(link, year):
    if db.year_locked(year):
        flash(f"{year} is locked! Come back next year!")
        return redirect(f"/{link}/{year}")
    elif db.user_playing(link, year):
        flash(f"You are already playing for {year}!")
        return redirect(f"/{link}/{year}")

    if request.method == "GET":
        return rt("rules.html", confirm_link=f"/{link}/{year}/play")

    if request.method == "POST":
        db.add_user_picks(link, year)
        db.add_paid_status(link, year)
        flash(f"You are playing in the {year} league. Good luck!")
        return redirect(f"/{link}/{year}")


@app.route("/<link>/<year>/retire", methods=["GET"])
@validate_link
@validate_email
@validate_year
def retire_year(link, year):
    if db.user_playing(link, year) and int(year) == db.get_current_year():
        db.set_retired(link, year)
        flash("You retired! See you next year!")
        return redirect(f"/{link}/{year}")

    flash("You can not retire since you are not playing!")
    return redirect(f"/{link}/{year}")


@app.route("/favicon.ico")
def favicon():
    root = os.path.join(app.root_path, "static")
    return sfd(root, "favicon.ico")


@app.route("/css/main.css")
def css():
    root = os.path.join(app.root_path, "static/css")
    return sfd(root, "main.css")


@app.route("/fonts/OpenSans-Regular.eot")
def font_eot():
    root = os.path.join(app.root_path, "static/fonts")
    return sfd(root, "OpenSans-Regular.eot")


@app.route("/fonts/OpenSans-Regular.ttf")
def font_ttf():
    root = os.path.join(app.root_path, "static/fonts")
    return sfd(root, "OpenSans-Regular.ttf")


@app.errorhandler(404)
def page_not_found(error):
    print(error)
    return rt("404.html"), 404
