from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

from .models import Activity, Quest


class ActivitySerializer(serializers.ModelSerializer):
    """Сериализатор модели должности"""

    class Meta:
        """Параметры сериализатора"""

        model = Activity
        fields = "__all__"


class QuestSerializer(serializers.ModelSerializer):
    """Сериализатор модели задачи"""

    class Meta:
        """Параметры сериализатора"""

        model = Quest
        fields = "__all__"


class QuestCreatingSerializer(serializers.ModelSerializer):
    """Сериализатор создания задачи"""

    creator = serializers.HiddenField(default=CurrentUserDefault())

    class Meta:
        """Параметры сериализатора"""

        model = Quest
        fields = ["title", "description", "creator", "dead_line", "related_quest", "operator", "required"]
