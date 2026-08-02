from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import CurrentUserDefault

from users.models import Employee

from .models import Activity, Quest
from .services import operator_auto_setting
from .validators import (
    check_operator_readiness,
    dead_line_validator,
    related_quest_subordination_validator,
)


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
        read_only_fields = ["id", "path_to_root", "status", "report"]

    def validate(self, attrs: dict) -> Any:
        """Комплексная валидация параметров обновляемой задачи"""

        dead_line_validator(attrs, quest=self.instance)
        check_operator_readiness(attrs, quest=self.instance)
        user = self.context["request"].user
        related_quest_subordination_validator(attrs, user, quest=self.instance)
        return super().validate(attrs)

    def update(self, instance: Quest, validated_data: dict) -> Quest:
        """Исправление значения поля path_to_root у всех подзадач при изменении ссылки на родительскую задачу"""

        instance = super().update(instance, validated_data)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if "related_quest" in validated_data:
            new_parent = validated_data["related_quest"]
            if new_parent and new_parent.pk == instance.pk:
                raise ValidationError("Задача не может быть задачей-родителем для самой себя")
            current_path = f"{instance.path_to_root}{instance.pk}/"
            childs = Quest.objects.filter(path_to_root__startswith=current_path)
            if not new_parent:
                instance.path_to_root = ""
            elif new_parent in childs:
                raise ValidationError(f"Попытка установить циклическую зависимость от задачи {new_parent.pk}")
            else:
                instance.path_to_root = f"{new_parent.path_to_root}{new_parent.pk}/"
            new_path = f"{instance.path_to_root}{instance.pk}/"
            update_list = list()
            for child in childs:
                updated_path = child.path_to_root.replace(current_path, new_path)
                child.path_to_root = updated_path
                update_list.append(child)
            Quest.objects.bulk_update(update_list, fields=["path_to_root"])
        if not isinstance(instance.operator, Employee):
            instance = operator_auto_setting(instance)
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

    def validate(self, attrs: dict) -> Any:
        """Комплексная валидация параметров создаваемой задачи"""

        dead_line_validator(attrs)
        check_operator_readiness(attrs)
        user = self.context["request"].user
        related_quest_subordination_validator(attrs, user)
        return super().validate(attrs)

    def create(self, validated_data: dict) -> Quest:
        """Формирование значения для поля path_to_root при сохранении объекта"""

        parent = validated_data.get("related_quest")
        if isinstance(parent, Quest):
            path_to_root = f"{parent.path_to_root}{parent.pk}/"
        else:
            path_to_root = ""
        quest = Quest(path_to_root=path_to_root, **validated_data)
        if not isinstance(quest.operator, Employee):
            quest = operator_auto_setting(quest)
        quest.save()
        return quest


class QuestSimplifiedSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для отображения списка задач"""

    operator = serializers.SerializerMethodField()
    required_activity = serializers.SerializerMethodField()

    class Meta:
        """Параметры сериализатора"""

        model = Quest
        fields = ["title", "operator", "required_activity", "dead_line", "status"]

    def get_operator(self, quest: Quest) -> str:
        """Определяет значение для поля operator"""

        if isinstance(quest.operator, Employee):
            operator = f"{quest.operator.last_name} {quest.operator.first_name}"
            if quest.operator.father_name:
                operator += f" {quest.operator.father_name}"
            return operator
        return "Исполнитель не назначен"

    def get_required_activity(self, quest: Quest) -> str:
        """Определяет значение для поля required_activity"""

        return str(quest.required.name)


class QuestUpdateReportSerializer(serializers.ModelSerializer):
    """Сериализатор отчета о стадии выполнения задачи"""

    class Meta:
        """Параметры сериализатора"""

        model = Quest
        fields = ["status", "report"]

    def validate(self, attrs: dict) -> Any:
        """Ограничивает допустимые устанавливаемые значения статуса выполнения задачи"""

        new_status = attrs.get("status", None)
        if new_status and new_status not in ["1_created", "2_processing", "3_sabotaged", "6_success"]:
            raise ValidationError("Исполнитель не может объявить задачу отмененной или просроченной")
        return super().validate(attrs)
