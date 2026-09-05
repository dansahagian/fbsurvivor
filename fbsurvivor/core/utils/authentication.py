import hashlib
import hmac
import secrets
from datetime import timedelta

from django.utils import timezone

from fbsurvivor.settings import SECRET_KEY

CODE_EXPIRATION_MINUTES = 15


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_code(code: str) -> str:
    return hmac.new(SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def calculate_expires_at():
    return timezone.now() + timedelta(minutes=CODE_EXPIRATION_MINUTES)
