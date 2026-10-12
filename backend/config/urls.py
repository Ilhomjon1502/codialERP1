from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAdminUser

admin.site.site_header = "Codial ERP — texnik boshqaruv"

urlpatterns = [
    path("api/v1/", include("config.api")),
    path("api/schema/", SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[IsAdminUser])),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    # Lokal ishlash: front-end Django orqali beriladi (serverda buni Nginx qiladi)
    urlpatterns += [
        path("", serve, {"path": "index.html", "document_root": settings.FRONTEND_DIR}),
        re_path(r"^(?P<path>(?!api/|admin/|static/).+)$", serve, {"document_root": settings.FRONTEND_DIR}),
    ]
