from django.contrib import admin
from django.urls import include, path
from drf_spectacular import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls", namespace="users")),
    path("", include("management.urls", namespace="management")),
    path("api/schema/", views.SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", views.SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", views.SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
