from django.contrib import admin
from django.http import FileResponse, HttpRequest
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from fbsurvivor import settings


@require_GET
@cache_control(max_age=60, immutable=True, public=True)
def favicon(request: HttpRequest) -> FileResponse:
    name = request.path.lstrip("/")
    file = (settings.BASE_DIR / "fbsurvivor" / "static" / "favicons" / name).open("rb")
    return FileResponse(file)


@require_GET
def font(request: HttpRequest) -> FileResponse:
    name = request.path.lstrip("/")
    file = (settings.BASE_DIR / "homepage" / "static" / "fonts" / name).open("rb")
    return FileResponse(file)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("fbsurvivor.core.urls")),
]

if settings.ENV == "dev":
    import debug_toolbar  # ruff: ignore

    local_urls = [
        path("android-chrome-192x192.png", favicon),
        path("android-chrome-512x512.png", favicon),
        path("apple-touch-icon.png", favicon),
        path("browserconfig.xml", favicon),
        path("favicon-16x16.png", favicon),
        path("favicon-32x32.png", favicon),
        path("favicon.ico", favicon),
        path("mstile-150x150.png", favicon),
        path("site.webmanifest", favicon),
        path("RobotoMono-Regular.woff", font),
        path("RobotoMono-Regular.woff2", font),
    ]

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns + local_urls
