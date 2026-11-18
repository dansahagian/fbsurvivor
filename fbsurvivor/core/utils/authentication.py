import hashlib
import hmac
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

from fbsurvivor.settings import SECRET_KEY

CODE_EXPIRATION_MINUTES = 15
CODE_MAX_TRIES = 3

# Each code allows CODE_MAX_TRIES guesses, so this caps guesses per account at
# CODE_SEND_MAX * CODE_MAX_TRIES per window and stops anyone flooding an inbox.
CODE_SEND_MAX = 5
CODE_SEND_WINDOW_SECONDS = 60 * 60


def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def generate_code_id() -> str:
    return secrets.token_urlsafe(16)


def _claim_slot(prefix: str, count: int, seconds: int) -> int | None:
    """Take the first free numbered slot, returning its number, or None if all are taken.

    add() inserts a new row, and the database's primary key lets only one concurrent
    caller win it. Counting with get()/incr() or with the session would let parallel
    requests all read the same count and share a single attempt.
    """
    for n in range(1, count + 1):
        if cache.add(f"{prefix}:{n}", True, seconds):
            return n
    return None


def claim_code_try(code_id: str) -> int | None:
    """Use up one guess at a code. Returns which guess this is, or None once none are left."""
    # code_id is random and never reused, so these rows are always brand new inserts.
    return _claim_slot(f"login-code-tries:{code_id}", CODE_MAX_TRIES, CODE_EXPIRATION_MINUTES * 60)


def claim_code_send(user: User | None, identifier: str) -> bool:
    """Count one code send against the account. False if it has hit the limit."""
    prefix = f"login-code-sends:{_account_suffix(user, identifier)}"
    return _claim_slot(prefix, CODE_SEND_MAX, CODE_SEND_WINDOW_SECONDS) is not None


def hash_code(code: str) -> str:
    return hmac.new(SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def calculate_expires_at():
    return timezone.now() + timedelta(minutes=CODE_EXPIRATION_MINUTES)


PASSWORD_MAX_FAILURES = 5
PASSWORD_LOCKOUT_SECONDS = 60 * 60


def find_user(identifier: str) -> User | None:
    """Match an email if it has an @, otherwise a username. Both ignore case."""
    if "@" in identifier:
        return User.objects.filter(email__iexact=identifier).first()
    return User.objects.filter(username__iexact=identifier).first()


def _account_suffix(user: User | None, identifier: str) -> str:
    # Key on the account when there is one, so its email and username share a single limit.
    # Unknown identifiers get limits too, so hitting one doesn't reveal that an account exists.
    return f"user:{user.pk}" if user else f"unknown:{identifier.lower()}"


def _password_attempts_prefix(user: User | None, identifier: str) -> str:
    return f"password-attempts:{_account_suffix(user, identifier)}"


def claim_password_attempt(user: User | None, identifier: str) -> bool:
    """Count an attempt before the password is checked. False if the account is locked out.

    Claiming first means parallel guesses each use up an attempt; checking a count and
    recording the failure afterwards let them all slip past the check together.
    Each attempt expires PASSWORD_LOCKOUT_SECONDS after it was made.
    """
    prefix = _password_attempts_prefix(user, identifier)
    return _claim_slot(prefix, PASSWORD_MAX_FAILURES, PASSWORD_LOCKOUT_SECONDS) is not None


def clear_password_attempts(user: User | None, identifier: str) -> None:
    prefix = _password_attempts_prefix(user, identifier)
    cache.delete_many([f"{prefix}:{n}" for n in range(1, PASSWORD_MAX_FAILURES + 1)])
