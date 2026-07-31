from datetime import datetime
from typing import Optional

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from management.models import Quest


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
