from rest_framework import serializers

from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    """Сериализатор модели должности"""

    class Meta:
        """Параметры сериализатора"""

        model = Activity
        fields = "__all__"
