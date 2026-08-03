from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .apps import ManagementConfig

app_name = ManagementConfig.name

management_router = DefaultRouter()
management_router.register("activities", views.ActivityViewSet)
management_router.register("quests", views.QuestViewSet)

urlpatterns: list = [
    path(
        "activities/<int:activity_pk>/partners/<int:partner_pk>/",
        views.ManageActivityRelationsView.as_view(),
        name="manage_relations",
    )
]
urlpatterns += management_router.urls
