from datetime import datetime
from hmac import compare_digest

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST

from fbsurvivor.core.forms import CodeForm, EmailForm
from fbsurvivor.core.models import Player
from fbsurvivor.core.utils.authentication import calculate_expires_at, generate_code, hash_code
from fbsurvivor.core.utils.emails import send_login_code
from fbsurvivor.core.views.board import board_redirect


def clean_session_data(request):
    request.session.pop("user_id", None)
    request.session.pop("email", None)
    request.session.pop("code_hash", None)
    request.session.pop("code_tries", None)
    request.session.pop("code_expires_at", None)


class IndexView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect(reverse("board_redirect"))

        request.session.flush()
        return render(request, "index.html", context={"form": EmailForm()})

    def post(self, request):
        form = EmailForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            code = generate_code()

            if user := User.objects.filter(email=email).first():
                send_login_code(user, code)
                request.session["user_id"] = user.pk

            request.session["email"] = email
            request.session["code_hash"] = hash_code(code)
            request.session["code_tries"] = 0
            request.session["code_expires_at"] = calculate_expires_at().isoformat()

        return redirect(reverse("login"))


class LoginView(View):
    def get(self, request):
        email = request.session.get("email", None)
        if email is None:
            return redirect(reverse("index"))

        context = {"form": CodeForm(), "email": email}
        return render(request, "login-sent.html", context=context)

    def post(self, request):
        if "email" not in request.session:
            clean_session_data(request)
            return render(request, "login-error-code.html")

        if timezone.now() > datetime.fromisoformat(request.session["code_expires_at"]):
            clean_session_data(request)
            return render(request, "login-error-code.html")

        code_tries = request.session["code_tries"] + 1
        form = CodeForm(request.POST)

        if not form.is_valid():
            context = {"form": form, "email": request.session["email"]}
            return render(request, "login-sent.html", context=context)

        if (user_id := request.session.get("user_id", None)) and compare_digest(
            request.session["code_hash"], hash_code(form.cleaned_data["code"])
        ):
            if user := User.objects.filter(id=user_id).first():
                login(request, user)
                clean_session_data(request)
                return redirect(reverse("board_redirect"))

        if code_tries > 2:
            clean_session_data(request)
            return render(request, "login-error-code-tries.html")

        request.session["code_tries"] = code_tries
        context = {"form": CodeForm(), "email": request.session["email"], "tries": 3 - code_tries}
        return render(request, "login-error-code-retry.html", context=context)


def clean_session(request):
    clean_session_data(request)
    return redirect(reverse("index"))


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
