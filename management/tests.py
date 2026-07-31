from datetime import datetime, timezone

from rest_framework import status
from rest_framework.test import APITestCase

from users.models import Employee

from .models import Activity, Quest


class ActivityTestCase(APITestCase):
    """Группа тестов для модели Activity"""

    fixtures = ["activities_fixture.json", "employees_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="7748IrIrde5b")
        self.client.force_authenticate(user=self.user)

    def test_activity_create(self) -> None:
        """Устройство нового сотрудника в организацию"""

        self.assertEqual(len(Activity.objects.all()), 12)
        new_activity_data = {"name": "Медсестра", "description": "Дежурный медик на производстве"}
        response = self.client.post("/activities/", new_activity_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(Activity.objects.all()), 13)
        response.data.pop("id")
        self.assertEqual(response.data, {"name": "Медсестра", "description": "Дежурный медик на производстве"})

    def test_activity_invalid_create(self) -> None:
        """Запрет создавать должности с одинаковыми названиями"""

        self.assertEqual(len(Activity.objects.all()), 12)
        new_activity_data = {"name": "Бухгалтер", "description": "Помощник главного бухгалтера"}
        response = self.client.post("/activities/", new_activity_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_getting_activities_list(self) -> None:
        """Отображение списка должностей"""

        response = self.client.get("/activities/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 12)

    def test_activity_retrieve(self) -> None:
        """Отображение объекта должности"""

        response = self.client.get("/activities/5/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response.data.pop("id")
        self.assertEqual(response.data, {"name": "Инженер-наладчик", "description": "Царь-фиксик"})

    def test_activity_update(self) -> None:
        """Изменение объекта должности"""

        response = self.client.put(
            "/activities/12/",
            data={
                "name": "Столяр-мебельщик",
                "description": "Распиловщик листовых материалов с опытом работы не менее года",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": 12,
                "name": "Столяр-мебельщик",
                "description": "Распиловщик листовых материалов с опытом работы не менее года",
            },
        )

    def test_unused_activity_delete(self) -> None:
        """Удаление незанятой должности"""

        self.assertEqual(len(Activity.objects.all()), 12)
        response = self.client.delete("/activities/7/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Activity.objects.all()), 11)

    def test_used_activity_fail_delete(self) -> None:
        """Попытка удаления занятой должности"""

        self.assertEqual(len(Activity.objects.all()), 12)
        response = self.client.delete("/activities/2/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class QuestTestCase(APITestCase):
    """Группа тестов для модели Quest"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "quests_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="8024IvIvc0e0")
        self.client.force_authenticate(user=self.user)

    def test_quest_creating(self) -> None:
        """Создание задачи"""

        self.assertEqual(len(Quest.objects.all()), 11)

        quest_data = {
            "title": "Помыть посуду",
            "description": "Быстро!",
            "related_quest": 9,
            "operator": 2,
            "required": 1,
            "dead_line": "2026-07-31T15:35:00.0Z",
        }
        response = self.client.post("/quests/", data=quest_data)
        new_quest = Quest.objects.get(title="Помыть посуду")
        response.data.pop("dead_line")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(Quest.objects.all()), 12)
        self.assertEqual(new_quest.creator.username, "8024IvIvc0e0")
        self.assertEqual(
            response.data,
            {
                "title": "Помыть посуду",
                "description": "Быстро!",
                "related_quest": 9,
                "operator": 2,
                "required": 1,
                "path_to_root": "4/6/8/9/",
            },
        )

    def test_getting_quest_list(self) -> None:
        """Получение списка задач"""

        response = self.client.get("/quests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 11)

    def test_quest_retrieve(self) -> None:
        """Отображение задачи"""

        response = self.client.get("/quests/8/")
        quest = response.data
        created_at = quest.pop("created_at")
        created_utc = str(datetime.fromisoformat(created_at).astimezone(timezone.utc))
        dead_line = quest.pop("dead_line")
        dead_line_utc = str(datetime.fromisoformat(dead_line).astimezone(timezone.utc))

        self.assertEqual(created_utc, "2026-07-31 14:19:29.311000+00:00")
        self.assertEqual(dead_line_utc, "2026-07-31 16:11:11.100000+00:00")
        self.assertEqual(
            response.data,
            {
                "id": 8,
                "title": "Нужен еще один инженер",
                "description": "Подать объявление, нужен толковый специалист-наладчик на производство",
                "creator": 2,
                "related_quest": 6,
                "operator": 3,
                "required": 3,
                "status": "4_expired",
                "report": "Интернет пропал, системный администратор был недоступен",
                "path_to_root": "4/6/",
            },
        )

    def test_quest_update_delete(self) -> None:
        """Изменение задачи и удаление подзадачи, неактуальной задачи"""

        self.assertEqual(len(Quest.objects.all()), 11)

        failed_delete = self.client.delete("/quests/6/")

        self.assertEqual(failed_delete.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(Quest.objects.all()), 11)

        task_4 = Quest.objects.get(title__startswith="Запустить")
        task_4_data = {"title": task_4.title, "description": task_4.description, "related_quest": task_4.related_quest}
        task_6 = Quest.objects.get(title__startswith="Нанять")
        task_6_data = {"title": task_6.title, "description": task_6.description, "related_quest": task_6.related_quest}
        task_9 = Quest.objects.get(title__startswith="Восстановить")
        task_9_data = {"title": task_9.title, "description": task_9.description, "related_quest": task_9.related_quest}
        task_8_path = Quest.objects.get(title__startswith="Нужен").path_to_root
        task_9_path = task_9.path_to_root

        self.assertEqual((task_8_path, task_9_path), ("4/6/", "4/6/8/"))

        response = self.client.patch(
            "/quests/8/",
            data={
                "title": "Задача 4 перенаправлена в отдел кадров",
                "description": "Директору некогда! Директор перенаправил заявку инженера в отдел кадров",
                "related_quest": 4,
            },
        )
        task_4_updated = Quest.objects.get(title__startswith="Запустить")
        task_4_data_updated = {
            "title": task_4_updated.title,
            "description": task_4_updated.description,
            "related_quest": task_4_updated.related_quest,
        }
        task_6_updated = Quest.objects.get(title__startswith="Нанять")
        task_6_data_updated = {
            "title": task_6_updated.title,
            "description": task_6_updated.description,
            "related_quest": task_6_updated.related_quest,
        }
        task_9_updated = Quest.objects.get(title__startswith="Восстановить")
        task_9_data_updated = {
            "title": task_9_updated.title,
            "description": task_9_updated.description,
            "related_quest": task_9_updated.related_quest,
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            (task_4_data, task_6_data, task_9_data), (task_4_data_updated, task_6_data_updated, task_9_data_updated)
        )

        updated_task_8 = Quest.objects.get(title__startswith="Задача 4")
        updated_task_9_path = Quest.objects.get(title__startswith="Восстановить").path_to_root

        self.assertEqual((updated_task_8.path_to_root, updated_task_9_path), ("4/", "4/8/"))
        self.assertEqual(
            updated_task_8.description, "Директору некогда! Директор перенаправил заявку инженера в отдел кадров"
        )

        success_delete = self.client.delete("/quests/6/")

        self.assertEqual(success_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Quest.objects.all()), 10)


class QuestSpecialTestCase(APITestCase):
    """Группа специфичных тестов для модели Quest"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "quests_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="8024IvIvc0e0")
        self.client.force_authenticate(user=self.user)

    def test_quest_dead_line_validator(self) -> None:
        """Проверка валидатора поля dead_line"""

        self.assertEqual(len(Quest.objects.all()), 11)

        quest_data = {
            "title": "Помыть посуду",
            "description": "Быстро!",
            "operator": 2,
            "required": 1,
            "dead_line": "2000-07-31T15:35:00.112233+07:00",
        }
        response_1 = self.client.post("/quests/", data=quest_data)

        self.assertEqual(response_1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("Срок выполнения задачи не может быть задан в прошлом" in str(response_1.data), True)
        self.assertEqual(len(Quest.objects.all()), 11)

        quest_data["dead_line"] = "2030-07-31T15:35:00.112233+07:00"
        response_2 = self.client.patch("/quests/6/", data=quest_data)

        self.assertEqual(response_2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(Quest.objects.all()), 11)
        self.assertEqual(
            "Срок выполнения текущей задачи не должен превышать срок выполнения зависимой от нее задачи"
            in str(response_2.data),
            True,
        )
