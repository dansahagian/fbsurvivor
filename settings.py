from decouple import config

ROOT_URL = config('ROOT_URL')

DEBUG = config('DEBUG')
SECRET_KEY = config('SECRET_KEY')

DATABASE = config('DATABASE')
PG_USER = config('PG_USER')
PG_PASSWORD = config('PG_PASSWORD')
PG_HOST = config('PG_HOST')
PG_PORT = config('PG_PORT')

SMTP_SERVER = config('SMTP_SERVER')
SMTP_SENDER = config('SMTP_SENDER')
SMTP_USER = config('SMTP_USER')
SMTP_PASSWORD = config('SMTP_PASSWORD')
SMTP_PORT = config('SMTP_PORT')
