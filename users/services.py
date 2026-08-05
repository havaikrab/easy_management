import secrets
from time import time

from unidecode import unidecode

from management.models import Activity
from management.services import get_operators_with_quests_for_activities


def generate_username(data: dict) -> str:
    """Генерирует уникальный идентификатор пользователя для поля username"""

    second = str(int(time()))[-4:]
    initials = f'{data['last_name'][:2]}{data["first_name"][:2]}'
    secret = secrets.token_hex(2)
    return unidecode(second + initials + secret)


def get_sorted_range_from_activ_operators(activity: Activity, reverse: bool = False) -> list[dict]:
    """Возвращает список доступных сотрудников определенной должности, отсортированный по количеству активных задач"""

    operators = get_operators_with_quests_for_activities(
        [activity], ["1_created", "2_processing", "3_sabotaged"], readiness=True
    )[str(activity.pk)]
    for value in operators.values():
        operator = value.pop("object")
        operator_data = {
            "id": operator.pk,
            "username": operator.username,
            "activity": operator.activity.name,
            "full_name": f"{operator.last_name} {operator.first_name}",
        }
        value["operator"] = operator_data
        quests = value.pop("quests")
        value["quests"] = list()
        for quest in quests:
            quest_dict = {
                "id": quest.pk,
                "title": quest.title,
                "created_at": str(quest.created_at),
                "dead_line": str(quest.dead_line),
                "status": quest.status,
            }
            value["quests"].append(quest_dict)
    sorted_list = sorted(list(operators.values()), key=lambda x: len(x["quests"]), reverse=reverse)
    return sorted_list
