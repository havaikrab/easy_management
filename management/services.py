from typing import Any

from django.db.models import Q, QuerySet

from management.models import Activity, Quest
from users.models import Employee


def get_operators_with_quests_for_activities(
    activities_list: list[Activity], quest_statuses: list, readiness: bool = True
) -> dict:
    """Возвращает сгруппированный по должностям словарь с объектами сотрудников и их задачами,
    имеющими соответствующий статус"""

    if readiness:
        readiness_status = "ready_to_work"
    else:
        readiness_status = "not_available"
    requested_operators = Employee.objects.filter(activity__in=activities_list, readiness=readiness_status)
    quests = Quest.objects.filter(operator__in=requested_operators)
    activities_dict = dict()
    for activity in activities_list:
        activity_employees = requested_operators.filter(activity=activity)
        operators: dict[str, Any] = {
            str(operator.pk): {"object": operator, "quests": list()} for operator in activity_employees
        }
        if len(operators) > 0:
            requested_tasks = quests.filter(
                status__in=quest_statuses,
                required=activity,
                operator__isnull=False,
                operator__readiness=readiness_status,
            )
            for quest in requested_tasks:
                quest_operator = quest.operator
                operators[str(quest_operator.pk)]["quests"].append(quest)
        activities_dict[str(activity.pk)] = operators
    return activities_dict


def get_candidates_for_important_quest(quest: Quest, activities_data: dict) -> list:
    """Возвращает список, потенциальных исполнителей задачи вместе со списками их текущих задач"""

    relevant_operators = activities_data.get(str(quest.required.pk), dict())
    if len(relevant_operators) > 0:
        if len(relevant_operators) > 1:
            less_busy = min(relevant_operators.values(), key=lambda pk: len(pk["quests"]))["object"]
            if isinstance(quest.related_quest, Quest) and isinstance(quest.related_quest.operator, Employee):
                related_quest_operator = quest.related_quest.operator
                key = str(related_quest_operator.pk)
                if key in relevant_operators:
                    less_busy_key = str(less_busy.pk)
                    count_difference = len(relevant_operators[key]["quests"]) - len(
                        relevant_operators[less_busy_key]["quests"]
                    )
                    if count_difference > 2:
                        relevant_operators.pop(key)
            return sorted(list(relevant_operators.values()), key=lambda pk: len(pk["quests"]))
        return list(relevant_operators.values())
    return list()


def get_candidates_names(quest: Quest, activities_data: dict) -> list:
    """Возвращает список с именами потенциальных исполнителей задачи"""

    candidates_list = get_candidates_for_important_quest(quest, activities_data)
    result = list()
    for candidate in candidates_list:
        candidate_str = f"{candidate["object"].last_name} {candidate["object"].first_name}"
        father_name = candidate["object"].father_name
        if father_name is not None:
            candidate_str += f" {father_name}"
        result.append(candidate_str)
    return result


def get_important_quests_with_candidates() -> list:
    """Возвращает список невыполняемых важных задач с соответствующими списками имен потенциальных исполнителей"""

    stopped_quests = Quest.objects.filter(Q(operator__isnull=True) | Q(status="3_sabotaged")).select_related(
        "required"
    )
    activity_ids = list(set([quest.required.pk for quest in stopped_quests]))
    required_activities = list(Activity.objects.filter(pk__in=activity_ids))
    activities_data = get_operators_with_quests_for_activities(
        required_activities, ["1_created", "2_processing", "3_sabotaged"]
    )
    result = list()
    for quest in stopped_quests:
        quest_dict = {"id": quest.pk, "title": quest.title, "dead_line": str(quest.dead_line)}
        candidates = get_candidates_names(quest, activities_data)
        if len(candidates) == 0:
            candidates = ["Подходящие специалисты для выполнения задачи не найдены."]
        quest_dict["candidates"] = candidates
        result.append(quest_dict)
    return result


def operator_auto_setting(quest: Quest) -> Quest:
    """Назначает или переопределяет исполнителя задачи, если он не указан или имеет статус Не доступен"""

    if quest.status in ["1_created", "2_processing", "3_sabotaged"]:
        operator = quest.operator
        if not isinstance(operator, Employee) or operator.readiness != "ready_to_work":
            activities_data = get_operators_with_quests_for_activities(
                [quest.required], ["1_created", "2_processing", "3_sabotaged"]
            )
            relevant_operators = get_candidates_for_important_quest(quest, activities_data)
            if len(relevant_operators) > 0:
                less_busy = relevant_operators[0]["object"]
                quest.operator = less_busy
                quest.report += f"\nСотрудник {less_busy.last_name} {less_busy.first_name} автоматически назначен ответственным исполнителем"  # noqa
                return quest
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
