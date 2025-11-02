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


@require_GET  # ty: ignore
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
        path("android-chrome-192x192.png", favicon),  # ty: ignore
        path("android-chrome-512x512.png", favicon),  # ty: ignore
        path("apple-touch-icon.png", favicon),  # ty: ignore
        path("browserconfig.xml", favicon),  # ty: ignore
        path("favicon-16x16.png", favicon),  # ty: ignore
        path("favicon-32x32.png", favicon),  # ty: ignore
        path("favicon.ico", favicon),  # ty: ignore
        path("mstile-150x150.png", favicon),  # ty: ignore
        path("site.webmanifest", favicon),  # ty: ignore
        path("RobotoMono-Regular.woff", font),  # ty: ignore
        path("RobotoMono-Regular.woff2", font),  # ty: ignore
    ]

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns + local_urls
