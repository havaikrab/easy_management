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
        read_only_fields = ["id", "path_to_root"]

    def update(self, instance: Quest, validated_data: dict) -> Quest:

        for k, v in validated_data.items():
            setattr(instance, k, v)
        if "related_quest" in validated_data:
            current_path = f"{instance.path_to_root}{instance.pk}/"
            childs = Quest.objects.filter(path_to_root__startswith=current_path)
            new_parent = validated_data["related_quest"]
            if new_parent is None:
                instance.path_to_root = ""
            else:
                instance.path_to_root = f"{new_parent.path_to_root}{new_parent.pk}/"
            new_path = f"{instance.path_to_root}{instance.pk}/"
            update_list = list()
            for child in childs:
                updated_path = child.path_to_root.replace(current_path, new_path)
                child.path_to_root = updated_path
                update_list.append(child)
            Quest.objects.bulk_update(update_list, fields=["path_to_root"])
        instance.save()
        return instance


class QuestCreatingSerializer(serializers.ModelSerializer):
    """Сериализатор создания задачи"""

    creator = serializers.HiddenField(default=CurrentUserDefault())

    class Meta:
        """Параметры сериализатора"""

        model = Quest
        fields = [
            "title",
            "description",
            "creator",
            "dead_line",
            "related_quest",
            "operator",
            "required",
            "path_to_root",
        ]
        read_only_fields = ["path_to_root"]

    def create(self, validated_data: dict) -> Quest:

        parent = validated_data.get("related_quest")
        if isinstance(parent, Quest):
            path_to_root = f"{parent.path_to_root}{parent.pk}/"
        else:
            path_to_root = ""
        return Quest.objects.create(path_to_root=path_to_root, **validated_data)
