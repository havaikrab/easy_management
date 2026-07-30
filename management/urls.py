from rest_framework.routers import DefaultRouter

from . import views
from .apps import ManagementConfig

app_name = ManagementConfig.name

management_router = DefaultRouter()
management_router.register("activities", views.ActivityViewSet)
management_router.register("quests", views.QuestViewSet)

urlpatterns = management_router.urls
