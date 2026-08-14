from django_filters.rest_framework import FilterSet

from management.models import Quest


class QuestFilterSet(FilterSet):
    """Фильтрсет для модели Quest"""

    class Meta:
        """Параметры фильтрсета"""

        model = Quest
        fields = {
            "title": ["icontains"],
            "description": ["icontains"],
            "creator": ["exact", "in"],
            "related_quest": ["exact"],
            "operator": ["exact", "in"],
            "required": ["exact"],
            "created_at": ["exact", "gt", "lt"],
            "dead_line": ["exact", "gt", "lt"],
            "status": ["exact"],
        }
