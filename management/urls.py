from rest_framework.routers import DefaultRouter

from . import views
from .apps import ManagementConfig

app_name = ManagementConfig.name

management_router = DefaultRouter()
management_router.register("activities", views.ActivityViewSet)

urlpatterns = management_router.urls
