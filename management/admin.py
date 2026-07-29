from django.contrib import admin

from .models import Activity, Quest


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    """Класс представления модели должности в админ-панели Django"""

    list_display = ("name", "description")
    search_fields = ("name",)
    list_filter = ("name",)


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    """Класс представления модели задачи в админ-панели Django"""

    list_display = (
        "title",
        "description",
        "related_quest",
        "operator",
        "required",
        "created_at",
        "dead_line",
        "status",
    )
    search_fields = ("title", "status", "required")
    list_filter = ("status", "required")
