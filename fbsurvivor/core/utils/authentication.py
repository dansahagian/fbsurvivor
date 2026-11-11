import hashlib
import hmac
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

from fbsurvivor.settings import SECRET_KEY

CODE_EXPIRATION_MINUTES = 15


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def hash_code(code: str) -> str:
    return hmac.new(SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def calculate_expires_at():
    return timezone.now() + timedelta(minutes=CODE_EXPIRATION_MINUTES)


PASSWORD_MAX_FAILURES = 5
PASSWORD_LOCKOUT_SECONDS = 60 * 15


def find_user(identifier: str) -> User | None:
    """Match an email if it has an @, otherwise a username. Both ignore case."""
    if "@" in identifier:
        return User.objects.filter(email__iexact=identifier).first()
    return User.objects.filter(username__iexact=identifier).first()


def password_failures_key(user: User | None, identifier: str) -> str:
    # Key on the account when there is one, so its email and username share a single limit.
    suffix = f"user:{user.pk}" if user else f"unknown:{identifier.lower()}"
    return f"password-failures:{suffix}"


def is_password_locked_out(key: str) -> bool:
    return cache.get(key, 0) >= PASSWORD_MAX_FAILURES


def record_password_failure(key: str) -> None:
    # add() is a no-op if the key exists, so the lockout window starts at the first failure.
    cache.add(key, 0, PASSWORD_LOCKOUT_SECONDS)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, PASSWORD_LOCKOUT_SECONDS)


def clear_password_failures(key: str) -> None:
    cache.delete(key)
