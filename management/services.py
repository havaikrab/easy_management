import logging
from typing import Any

from django.db.models import QuerySet

from management.models import Activity, Quest
from users.models import Employee

logger = logging.getLogger(__name__)


def get_operators_with_quests(activity: Activity, quest_statuses: list, readiness: bool = True) -> dict:
    """Возвращает словарь с объектами сотрудников, с их задачами, имеющими соответствующий статус"""

    if readiness:
        readiness_status = "ready_to_work"
    else:
        readiness_status = "not_available"
    requested_operators = Employee.objects.filter(activity=activity, readiness=readiness_status)
    operators: dict[str, Any] = {
        str(operator.pk): {"object": operator, "quests": list()} for operator in requested_operators
    }
    if len(operators) > 0:
        requested_tasks = Quest.objects.filter(
            status__in=quest_statuses, required=activity, operator__isnull=False, operator__readiness=readiness_status
        )
        for quest in requested_tasks:
            quest_operator = quest.operator
            operators[str(quest_operator.pk)]["quests"].append(quest)
    return operators


def operator_auto_setting(quest: Quest) -> Quest:
    """Назначает или переопределяет исполнителя задачи, если он не указан или имеет статус Не доступен"""

    if quest.status in ["1_created", "2_processing", "3_sabotaged"]:
        operator = quest.operator
        activity = quest.required
        if not isinstance(operator, Employee) or operator.readiness != "ready_to_work":
            relevant_operators = get_operators_with_quests(activity, ["1_created", "2_processing"])
            if len(relevant_operators) > 0:
                less_busy = min(relevant_operators.values(), key=lambda pk: len(pk["quests"]))["object"]
                if isinstance(quest.related_quest, Quest) and quest.related_quest.required == quest.required:
                    for value in relevant_operators.values():
                        if quest.related_quest in value["quests"]:
                            related_quest_operator = value["object"]
                            difference = len(value["quests"]) - len(relevant_operators[str(less_busy.pk)]["quests"])
                            if difference <= 2:
                                quest.operator = related_quest_operator
                                quest.report += f'\nСотрудник ID "{related_quest_operator.username}" автоматически назначен ответственным исполнителем'  # noqa
                                return quest
                quest.operator = less_busy
                quest.report += (
                    f'\nСотрудник ID "{less_busy.username}" автоматически назначен ответственным исполнителем'
                )
            else:
                quest.status = "3_sabotaged"
                quest.report += "\nВыполнение задачи прервано. Исполнитель не может быть назначен автоматически"
    return quest


def set_activity_relation(patron: Activity, arrived: Activity) -> None:
    """Создает отношения между должностями"""

    if not patron.partners.filter(pk=arrived.pk).exists():
        patron.partners.add(arrived)


def get_quest_child_tree(quest: Quest, queryset: QuerySet) -> dict:
    """Возвращает словарь с характеристикой задачи и структурой ее подзадач"""

    path_with_parent = f"{quest.path_to_root}{quest.pk}/"
    return {
        "quest": {
            "title": quest.title,
            "description": quest.description,
            "creator": f"{quest.creator.activity.name}: {quest.creator.last_name} {quest.creator.first_name}",
            "operator": f"{quest.operator.activity.name}: {quest.operator.last_name} {quest.operator.first_name}",
            "created_at": str(quest.created_at),
            "dead_line": str(quest.dead_line),
            "status": quest.status,
            "report": quest.report,
            "path_to_root": quest.path_to_root,
        },
        "sub_quests": {
            str(sub.pk): get_quest_child_tree(
                sub, queryset.filter(path_to_root__startswith=f"{path_with_parent}{sub.pk}/")
            )
            for sub in queryset.filter(related_quest__pk=quest.pk)
        },
    }


def get_sub_quests_map(quest: Quest) -> dict:
    """Получает из базы данных все подзадачи указанной задачи,
    возвращает подробную карту зависимостей этих задач"""

    path_with_parent = f"{quest.path_to_root}{quest.pk}/"
    queryset = Quest.objects.filter(path_to_root__startswith=path_with_parent)
    return get_quest_child_tree(quest, queryset)
