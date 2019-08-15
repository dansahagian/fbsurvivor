from functools import wraps

from flask import abort
from flask import render_template

import db


def validate_link(func):
    @wraps(func)
    def wrapper(**kwargs):
        if db.valid_link(kwargs['link']):
            return func(**kwargs)
        return abort(404)
    return wrapper


def validate_year(func):
    @wraps(func)
    def wrapper(**kwargs):
        if db.valid_year(kwargs['year']):
            return func(**kwargs)
        return abort(404)
    return wrapper


def validate_week(func):
    @wraps(func)
    def wrapper(**kwargs):
        if db.valid_week(kwargs['week']):
            return func(**kwargs)
        return abort(404)
    return wrapper


def validate_email(func):
    @wraps(func)
    def wrapper(**kwargs):
        if db.email_confirmed(kwargs['link']):
            return func(**kwargs)
        return render_template('not-confirmed.html')
    return wrapper


def validate_admin(func):
    @wraps(func)
    def wrapper(**kwargs):
        if db.is_admin(kwargs['link']):
            return func(**kwargs)
        return abort(404)
    return wrapper
