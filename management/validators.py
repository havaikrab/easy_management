from datetime import datetime
from typing import Optional

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from management.models import Quest
from users.models import Employee


def dead_line_validator(quest_data: dict, quest: Optional[Quest] = None) -> None:
    """Проверяет корректность значения для поля dead_line при создании или обновлении объекта модели Quest"""

    dead_line = quest_data.get("dead_line")
    related_quest = quest_data.get("related_quest")
    if isinstance(dead_line, datetime):
        if timezone.now() >= dead_line:
            raise ValidationError("Срок выполнения задачи не может быть задан в прошлом")
        if (isinstance(related_quest, Quest) and related_quest.dead_line < dead_line) or (
            quest and quest.related_quest and quest.related_quest.dead_line < dead_line
        ):
            raise ValidationError(
                "Срок выполнения текущей задачи не должен превышать срок выполнения зависимой от нее задачи"
            )


def check_operator_readiness(quest_data: dict, quest: Optional[Quest] = None) -> None:
    """Проверяет общее соответствие исполнителя требованиям задачи"""

    required_activity = None
    candidate = None
    if quest:
        required_activity = quest.required
        candidate = quest.operator
    expected_required = quest_data.get("required", required_activity)
    expected_operator = quest_data.get("operator", candidate)
    if isinstance(expected_operator, Employee):
        if expected_operator.activity != expected_required:
            raise ValidationError("Должность исполнителя не соответствует требованиям задачи")
        if expected_operator.readiness == "automated":
            raise ValidationError("Автоматизированные системы не могут назначаться в качестве исполнителя задачи")
        if expected_operator.readiness == "not_available":
            raise ValidationError('Сотрудник имеет статус "Не доступен" и не может быть назначен исполнителем')
