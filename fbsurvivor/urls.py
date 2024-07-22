from django.contrib import admin
from django.http import FileResponse
from django.urls import include, path
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from fbsurvivor import settings


@require_GET
@cache_control(max_age=60, immutable=True, public=True)
def favicon_file(request):
    name = request.path.lstrip("/")
    file = (settings.BASE_DIR / "fbsurvivor" / "static" / "favicons" / name).open("rb")
    return FileResponse(file)


@require_GET
def font_file(request):
    name = request.path.lstrip("/")
    file = (settings.BASE_DIR / "homepage" / "static" / "fonts" / name).open("rb")
    return FileResponse(file)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("fbsurvivor.core.urls")),
]

if settings.ENV == "dev":
    import debug_toolbar

    local_urls = [
        path("android-chrome-192x192.png", favicon_file),
        path("android-chrome-512x512.png", favicon_file),
        path("apple-touch-icon.png", favicon_file),
        path("browserconfig.xml", favicon_file),
        path("favicon-16x16.png", favicon_file),
        path("favicon-32x32.png", favicon_file),
        path("favicon.ico", favicon_file),
        path("mstile-150x150.png", favicon_file),
        path("site.webmanifest", favicon_file),
        path("RobotoMono-Regular.woff", font_file),
        path("RobotoMono-Regular.woff2", font_file),
    ]

    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns + local_urls
