import os
from flask import Flask, flash, redirect, request, abort
from flask import render_template as rt
from flask import send_from_directory as sfd
import db


app = Flask(__name__)
app.secret_key = os.environ['FLASK_KEY']


@app.route('/', methods=['GET'])
def index():
    return rt('index.html')


@app.route('/survive', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return rt('signup.html')

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'].lower()

        if len(username) > 20:
            flash('Username is greater than 20 characters! Choose again.')
            return redirect('/survive')

        if db.username_available(username):
            link = db.add_user(username, email)
            return redirect('/%s' % (link))

        flash('Username already exists! Pick another!')
        return redirect('/survive')


@app.route('/<link>', methods=['GET'])
def user(link):
    if db.valid_link(link):
        data = db.get_board(db.get_current_year())
        return rt('user.html', years=db.get_years(), link=link, data=data,
                  admin=db.user_admin(link))
    else:
        abort(404)


@app.route('/<link>/previous/<year>', methods=['GET'])
def previous(link, year):
    if db.valid_link(link):
        data = db.get_board(year)
        return rt('board.html', link=link, year=year, data=data,
                  years=db.get_years())
    else:
        abort(404)


@app.route('/<link>/<year>', methods=['GET'])
def picks(link, year):
    if db.valid_link(link):
        picks = db.get_user_picks(link, year)
        wins = len([x[2] for x in picks if x[2] == 'W'])
        loss = len([x[2] for x in picks if x[2] == 'L'])
        return rt('picks.html', link=link, year=year,
                  lock=db.year_locked(year), picks=picks, ws=wins, ls=loss)
    else:
        abort(404)


@app.route('/<link>/<year>/<week>', methods=['GET', 'POST'])
def pick(link, year, week):
    if db.valid_link(link):
        if request.method == 'GET':
            if db.week_locked(year, week):
                flash('Week %s is locked! Cannot Edit!' % (week))
                return redirect('/%s/%s' % (link, year))
            teams = db.get_team_choices(link, year, week)
            pick = db.get_current_pick(link, year, week)
            return rt('pick.html', link=link, year=year, week=int(week),
                      pick=pick, c=teams)

        if request.method == 'POST':
            picks = [x[1] for x in db.get_user_picks(link, year)]
            pick = request.form['pick']

            if pick in picks and pick != '--':
                flash('Pick NOT updated! %s already used.' % (pick))
            else:
                db.update_pick(link, year, week, pick)
                flash('Pick updated! Week %s: %s' % (week, pick))
                return redirect('/%s/%s' % (link, year))
    else:
        abort(404)


@app.route('/<link>/<year>/play', methods=['GET'])
def play_year(link, year):
    if db.valid_link(link):
        if db.year_locked(year):
            flash('%s is locked! Come back next year!' % (year))
            return redirect('/%s' % (link))
        elif db.user_playing(link, year):
            flash('You are already playing for %s' % (year))
            return redirect('/%s' % (link))
        else:
            db.add_user_picks(link, year)
            db.add_paid_status(link, year)
            flash('You are playing in the %s league. Good luck!' % (year))
            return redirect('/%s' % (link))
    else:
        abort(404)


@app.route('/<link>/admin', methods=['GET'])
def admin(link):
    if db.valid_link(link):
        if db.user_admin(link):
            return 'admin page'
        else:
            flash('You do NOT have access to that page!')
            return redirect('/%s' % (link))
    else:
        abort(404)


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
def page_not_found(error):
    return rt('404.html'), 404
