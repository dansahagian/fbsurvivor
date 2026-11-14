from datetime import datetime
from hmac import compare_digest

from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST

from fbsurvivor.core.forms import CodeForm, NewPasswordForm, SignInForm
from fbsurvivor.core.models import Player
from fbsurvivor.core.utils.authentication import (
    CODE_MAX_TRIES,
    calculate_expires_at,
    claim_code_send,
    claim_code_try,
    clear_password_failures,
    find_user,
    generate_code,
    generate_code_id,
    hash_code,
    is_password_locked_out,
    password_failures_key,
    record_password_failure,
)
from fbsurvivor.core.utils.emails import send_login_code, send_password_changed
from fbsurvivor.core.views.board import board_redirect


def clean_session_data(request):
    request.session.pop("user_id", None)
    request.session.pop("identifier", None)
    request.session.pop("code_hash", None)
    request.session.pop("code_id", None)
    request.session.pop("code_expires_at", None)


class IndexView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse("board_redirect"))

        request.session.flush()
        return render(request, "index.html", context={"form": SignInForm()})

    def post(self, request):
        form = SignInForm(request.POST)

        if not form.is_valid():
            return render(request, "index.html", context={"form": form})

        identifier = form.cleaned_data["identifier"]
        user = find_user(identifier)

        if password := form.cleaned_data["password"]:
            return self.password_login(request, form, user, identifier, password)

        if not claim_code_send(user, identifier):
            error = "Too many login codes requested. Try again in an hour."
            return render(request, "index.html", context={"form": form, "error": error})

        # Drop any earlier pending login so a stale user_id can't pair with this code.
        clean_session_data(request)
        code = generate_code()

        if user:
            send_login_code(user, code)
            request.session["user_id"] = user.pk

        request.session["identifier"] = identifier
        request.session["code_hash"] = hash_code(code)
        request.session["code_id"] = generate_code_id()
        request.session["code_expires_at"] = calculate_expires_at().isoformat()

        return redirect(reverse("login"))

    def password_login(self, request, form, user, identifier, password):
        key = password_failures_key(user, identifier)

        if is_password_locked_out(key):
            error = "Too many attempts. Leave the password blank to get a login code."
            return render(request, "index.html", context={"form": form, "error": error})

        if user is None:
            # Hash anyway so an unknown account takes as long as a wrong password.
            User().set_password(password)
        elif user.check_password(password):
            clear_password_failures(key)
            login(request, user)
            return redirect(reverse("board_redirect"))

        record_password_failure(key)
        error = "Incorrect login or password. Leave the password blank to get a login code."
        return render(request, "index.html", context={"form": form, "error": error})


class LoginView(View):
    def get(self, request):
        identifier = request.session.get("identifier", None)
        if identifier is None:
            return redirect(reverse("index"))

        context = {"form": CodeForm(), "identifier": identifier}
        return render(request, "login-sent.html", context=context)

    def post(self, request):
        if "identifier" not in request.session or "code_id" not in request.session:
            clean_session_data(request)
            return render(request, "login-error-code.html")

        if timezone.now() > datetime.fromisoformat(request.session["code_expires_at"]):
            clean_session_data(request)
            return render(request, "login-error-code.html")

        form = CodeForm(request.POST)

        if not form.is_valid():
            context = {"form": form, "identifier": request.session["identifier"]}
            return render(request, "login-sent.html", context=context)

        # Count the try before checking the code, so parallel guesses can't share one.
        code_try = claim_code_try(request.session["code_id"])
        if code_try is None:
            clean_session_data(request)
            return render(request, "login-error-code-tries.html")

        if (user_id := request.session.get("user_id", None)) and compare_digest(
            request.session["code_hash"], hash_code(form.cleaned_data["code"])
        ):
            if user := User.objects.filter(id=user_id).first():
                login(request, user)
                clean_session_data(request)
                return redirect(reverse("board_redirect"))

        if code_try >= CODE_MAX_TRIES:
            clean_session_data(request)
            return render(request, "login-error-code-tries.html")

        context = {
            "form": CodeForm(),
            "identifier": request.session["identifier"],
            "tries": CODE_MAX_TRIES - code_try,
        }
        return render(request, "login-error-code-retry.html", context=context)


def clean_session(request):
    clean_session_data(request)
    return redirect(reverse("index"))


@login_required
def set_password(request):
    # Players created by the manager have password="", which Django counts as usable.
    has_password = bool(request.user.password) and request.user.has_usable_password()
    # Passed so base.html applies the player's theme; staff may not have a Player.
    player = Player.objects.filter(user=request.user).first()
    form = NewPasswordForm(request.user, request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        send_password_changed(user)
        context = {"changed": has_password, "player": player}
        return render(request, "set-password-success.html", context=context)

    context = {"form": form, "has_password": has_password, "player": player}
    return render(request, "set-password.html", context=context)


def logout_view(request):
    logout(request)
    return render(request, "logout-success.html")


@login_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def theme(request, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    player.is_dark_mode = not player.is_dark_mode
    player.save()

    return board_redirect(request)


@login_required  # ty: ignore[no-matching-overload]
@require_POST  # ty: ignore[invalid-argument-type]
def update_reminders(request, kind, status, **kwargs):
    user = request.user
    player = get_object_or_404(Player, user=user)

    statuses = {
        "on": True,
        "off": False,
    }

    if status not in statuses or kind != "email":
        raise Http404

    player.has_email_reminders = statuses[status]

    player.save()

    return board_redirect(request)
