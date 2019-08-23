from flask import Flask
from survive import survive
from survive.settings import *

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.debug = DEBUG

app.register_blueprint(survive.bp)

