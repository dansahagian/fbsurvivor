import os
from flask import Flask, flash, redirect, request, abort
from flask import render_template as rt
from flask import send_from_directory as sfd
import db
import emailer


app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']


def valid_link(func):
    def inner(link):
        if db.valid_link(link):

            return func
        abort(404)

    return inner


def valid_year(func):
    def inner(year):
        if db.valid_year(year):

            return func
        abort(404)

    return inner


def valid_week(func):
    def inner(week):
        if db.valid_week(week):

            return func
        abort(404)

    return inner


@app.route('/', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':

        return rt('signup.html')

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'].lower()

        if len(str(username)) > 20:
            flash('Username is greater than 20 characters! Choose again.')

            return redirect('/')

        if db.username_available(username):
            link = db.add_user(username, email)
            confirm_link = f'https://fbsurvivor.com/{link}/confirm'
            subject = 'Confirm your Email - Football Survivor'
            message = f'Confirm your email address by clicking the link below:\n{confirm_link}'

            emailer.send_email(subject, [email], message)

            return rt('email.html')

        flash('Username already exists! Pick another!')

        return redirect('/')


@valid_link
@app.route('/<link>', methods=['GET'])
def dash(link):
    year = db.get_current_year()

    return redirect(f'/{link}/{year}')


@valid_link
@app.route('/<link>/confirm', methods=['GET'])
def confirm(link):
    year = db.get_current_year()
    email = db.get_email(link)
    db.confirm_email(link)

    user_link = f'https://fbsurvivor.com/{link}'
    subject = 'Football Survivor Link'
    message = f'Use this link to make your picks and check the board:\n{user_link}'

    emailer.send_email(subject, [email], message)

    flash('Email Confirmed! We have sent your custom link to your email.')

    return redirect(f'/{link}/{year}')


@valid_link
@valid_year
@app.route('/<link>/<year>', methods=['GET'])
def user(link, year):
    username = db.get_username(link)
    data = db.get_board(year)
    years = db.get_years()
    play = db.user_playing(link, year)
    retire = (not db.user_retired(link, year)) and (int(year) == db.get_current_year())

    return rt('user.html', years=years, link=link, data=data, username=username, year=year, play=play, retire=retire)


@valid_link
@valid_year
@app.route('/<link>/<year>/picks', methods=['GET'])
def picks(link, year):
    user_picks = db.get_user_picks(link, year)
    wins = len([x[2] for x in user_picks if x[2] == 'W'])
    loss = len([x[2] for x in user_picks if x[2] == 'L'])

    return rt('picks.html', link=link, year=year, lock=db.year_locked(year), picks=user_picks, ws=wins, ls=loss)


@valid_link
@valid_year
@valid_week
@app.route('/<link>/<year>/picks/<week>', methods=['GET', 'POST'])
def pick(link, year, week):
    teams = db.get_team_choices(link, year, week)

    if request.method == 'GET':
        if db.week_locked(year, week):
            flash(f'Week {week} is locked! Cannot Edit!')
            return redirect(f'/{link}/{year}/picks')
        user_pick = db.get_current_pick(link, year, week)

        return rt('pick.html', link=link, year=year, week=int(week), pick=user_pick, c=teams)

    if request.method == 'POST':
        user_picks = [x[1] for x in db.get_user_picks(link, year)]
        user_pick = request.form['pick']

        if user_pick in teams:
            if user_pick in user_picks and user_pick != '--':
                flash(f'Pick NOT updated! {user_pick} already used.')
            else:
                db.update_pick(link, year, week, user_pick)
                flash(f'Pick updated! Week {week}: {user_pick}')

                return redirect(f'/{link}/{year}/picks')
        flash(f'{user_pick} is not a valid choice!')
        return redirect(f'/{link}/{year}/picks')


@valid_link
@valid_year
@app.route('/<link>/<year>/play', methods=['GET'])
def play_year(link, year):
    if db.year_locked(year):
        flash(f'{year} is locked! Come back next year!')

        return redirect(f'/{link}/{year}')

    elif db.user_playing(link, year):
        flash(f'You are already playing for {year}')

        return redirect(f'/{link}/{year}')

    else:
        db.add_user_picks(link, year)
        db.add_paid_status(link, year)
        flash(f'You are playing in the {year} league. Good luck!')

        return redirect(f'/{link}/{year}')


@valid_link
@valid_year
@app.route('/<link>/<year>/retire', methods=['GET'])
def retire_year(link, year):
    if db.user_playing(link, year) and int(year) == db.get_current_year():
        db.set_retired(link, year)
        flash('You retired! See you next year!')

        return redirect(f'/{link}/{year}')
    flash('You can not retire since you are not playing!')

    return redirect(f'/{link}/{year}')


@app.route('/favicon.ico')
def favicon():
    root = os.path.join(app.root_path, 'static')

    return sfd(root, 'favicon.ico')


@app.route('/css/main.css')
def css():
    root = os.path.join(app.root_path, 'static/css')

    return sfd(root, 'main.css')


@app.route('/fonts/OpenSans-Regular.eot')
def font_eot():
    root = os.path.join(app.root_path, 'static/fonts')

    return sfd(root, 'OpenSans-Regular.eot')


@app.route('/fonts/OpenSans-Regular.ttf')
def font_ttf():
    root = os.path.join(app.root_path, 'static/fonts')

    return sfd(root, 'OpenSans-Regular.ttf')


@app.errorhandler(404)
def page_not_found():

    return rt('404.html'), 404
