from datetime import datetime, timezone

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import Employee

from .models import Activity, Quest
from .services import get_operators_with_quests


class ActivityTestCase(APITestCase):
    """Группа тестов для модели Activity"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "permissions_fixture.json"]

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
        self.assertEqual(
            response.data, {"name": "Медсестра", "description": "Дежурный медик на производстве", "partners": []}
        )

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
        response.data.pop("id")
        partners = response.data.pop("partners")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"name": "Инженер-наладчик", "description": "Царь-фиксик"})
        self.assertEqual(set(partners), {1, 2, 3, 6, 8, 11, 12})

    def test_activity_update(self) -> None:
        """Изменение объекта должности"""

        response = self.client.put(
            "/activities/12/",
            data={
                "name": "Столяр-мебельщик",
                "description": "Распиловщик листовых материалов с опытом работы не менее года",
                "partners": [5, 6, 8, 9],
            },
        )
        partners = response.data.pop("partners")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": 12,
                "name": "Столяр-мебельщик",
                "description": "Распиловщик листовых материалов с опытом работы не менее года",
            },
        )
        self.assertEqual(set(partners), {5, 6, 8, 9})

    def test_unused_activity_delete(self) -> None:
        """Удаление незанятой должности"""

        partner = Activity.objects.get(name__startswith="Менеджер")
        partners_ids = set([employee.pk for employee in partner.partners.all()])

        self.assertEqual(len(Activity.objects.all()), 12)
        self.assertEqual(partners_ids, {1, 2, 3, 4, 6, 7, 8, 10, 11, 12})

        response = self.client.delete("/activities/7/")
        updated_partner = Activity.objects.get(name__startswith="Менеджер")
        updated_partners_ids = set([employee.pk for employee in updated_partner.partners.all()])

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Activity.objects.all()), 11)
        self.assertEqual(updated_partners_ids, {1, 2, 3, 4, 6, 8, 10, 11, 12})

    def test_used_activity_fail_delete(self) -> None:
        """Попытка удаления занятой должности"""

        self.assertEqual(len(Activity.objects.all()), 12)
        response = self.client.delete("/activities/2/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activity_relations_addition(self) -> None:
        """Добавление связи между двумя должностями"""

        activity_1 = Activity.objects.get(name="Генеральный директор")
        activity_3 = self.user.activity
        activity_12 = Activity.objects.get(name="Столяр")

        self.assertEqual(len(activity_3.partners.all()), 5)

        bad_response = self.client.post(f"/activities/{activity_3.pk}/partners/{activity_1.pk}/")

        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_response.data, {"error": "Связь между должностями уже существует"})
        self.assertEqual(len(self.user.activity.partners.all()), 5)

        success_response = self.client.post(f"/activities/{activity_3.pk}/partners/{activity_12.pk}/")

        self.assertEqual(success_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            success_response.data,
            {"message": "Установлена связь между должностями Начальник отдела кадров и Столяр."},
        )
        self.assertEqual(len(self.user.activity.partners.all()), 6)

    def test_activity_relations_remove(self) -> None:
        """Ограничение связи между двумя должностями"""

        activity_1 = Activity.objects.get(name="Генеральный директор")
        activity_3 = self.user.activity
        activity_12 = Activity.objects.get(name="Столяр")

        self.assertEqual(len(activity_3.partners.all()), 5)

        bad_response = self.client.delete(f"/activities/{activity_3.pk}/partners/{activity_12.pk}/")

        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_response.data, {"error": "Связь между должностями не существует"})
        self.assertEqual(len(self.user.activity.partners.all()), 5)

        success_response = self.client.delete(f"/activities/{activity_3.pk}/partners/{activity_1.pk}/")

        self.assertEqual(success_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            success_response.data,
            {"message": "Связь между должностями Начальник отдела кадров и Генеральный директор исключена."},
        )
        self.assertEqual(len(self.user.activity.partners.all()), 4)


class QuestTestCase(APITestCase):
    """Группа тестов для модели Quest"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "quests_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="8024IvIvc0e0")
        self.client.force_authenticate(user=self.user)

    @freeze_time("2026-07-30T15:35:00.0Z")
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

    @freeze_time("2026-07-31T16:11:00.1Z")
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
        task_8 = Quest.objects.get(title__startswith="Нужен")
        task_8_path = task_8.path_to_root
        task_9_path = task_9.path_to_root

        self.assertEqual((task_8_path, task_9_path), ("4/6/", "4/6/8/"))

        denied_response = self.client.patch(
            "/quests/8/",
            data={
                "title": "Задача 4 перенаправлена в отдел кадров",
                "description": "Директору некогда! Директор перенаправил заявку инженера в отдел кадров",
                "related_quest": 4,
            },
        )

        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)

        task_8.creator = self.user
        task_8.save()
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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        task_4.creator = self.user
        task_4.save()
        tricky_admin_response = self.client.patch(
            "/quests/8/",
            data={
                "title": "Задача 4 перенаправлена в отдел кадров",
                "description": "Директору некогда! Директор перенаправил заявку инженера в отдел кадров",
                "related_quest": 4,
            },
        )

        self.assertEqual(tricky_admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            (task_4_data, task_6_data, task_9_data), (task_4_data_updated, task_6_data_updated, task_9_data_updated)
        )

        updated_task_8 = Quest.objects.get(title__startswith="Задача 4")
        updated_task_9_path = Quest.objects.get(title__startswith="Восстановить").path_to_root

        self.assertEqual((updated_task_8.path_to_root, updated_task_9_path), ("4/", "4/8/"))
        self.assertEqual(
            updated_task_8.description, "Директору некогда! Директор перенаправил заявку инженера в отдел кадров"
        )

        task_6.creator = self.user
        task_6.save()
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

        self.assertEqual(response_2.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(len(Quest.objects.all()), 11)
        self.assertEqual(
            "Для изменения объекта задачи нужно быть ее создателем или исполнителем" in str(response_2.data),
            True,
        )

    @freeze_time("2026-07-31T19:45:00.0Z")
    def test_checking_operator_readiness(self) -> None:
        """Проверка соответствия назначаемого сотрудника требованиям задачи"""

        quest_data = {
            "title": "Подмести цех",
            "description": "Директор ругается, что на производстве бардак, нужно подмести в цехе",
            "dead_line": "2026-08-01T19:45:00.0Z",
        }
        response_1 = self.client.post("/quests/", data=quest_data)

        self.assertEqual(response_1.status_code, status.HTTP_400_BAD_REQUEST)

        quest_data["required"] = "8"
        response_2 = self.client.post("/quests/", data=quest_data)
        response_2.data.pop("dead_line")
        operator_pk = response_2.data.pop("operator")

        self.assertEqual(response_2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(operator_pk in [5, 6], True)
        self.assertEqual(
            response_2.data,
            {
                "title": "Подмести цех",
                "description": "Директор ругается, что на производстве бардак, нужно подмести в цехе",
                "related_quest": None,
                "required": 8,
                "path_to_root": "",
            },
        )

        new_quest = Quest.objects.get(title__startswith="Подмести")

        response_3 = self.client.patch(f"/quests/{new_quest.pk}/", data={"operator": 12})
        self.assertEqual(response_3.status_code, status.HTTP_400_BAD_REQUEST)

        response_4 = self.client.patch(f"/quests/{new_quest.pk}/", data={"operator": 8})
        self.assertEqual(response_4.status_code, status.HTTP_400_BAD_REQUEST)

        response_5 = self.client.patch(f"/quests/{new_quest.pk}/", data={"required": 10, "operator": 11})
        self.assertEqual(response_5.status_code, status.HTTP_400_BAD_REQUEST)

    def test_getting_operators_with_quests(self) -> None:
        """Тест функции get_operators_with_quests"""

        required_activity = Activity.objects.get(name="Слесарь")
        new_task = {
            "title": "Подмести цех",
            "description": "Директор ругается, что на производстве бардак, нужно подмести в цехе",
            "operator": 5,
            "required": required_activity.pk,
            "dead_line": "2026-10-01T19:45:00.0Z",
        }
        response_post = self.client.post("/quests/", data=new_task)

        self.assertEqual(response_post.status_code, status.HTTP_201_CREATED)

        operators_1 = get_operators_with_quests(required_activity, ["1_created", "6_success"])
        operator_5 = Employee.objects.get(username="8064AlAla551")
        operator_6 = Employee.objects.get(username="8068DaDa0b6d")
        operator_7 = Employee.objects.get(username="8024IvIvhds0")
        operator_8 = Employee.objects.get(username="7753AlAlls6s")
        quest_7 = Quest.objects.get(title__startswith="Подготовить место")
        quest_12 = Quest.objects.get(title__startswith="Подмести")

        self.assertEqual(
            operators_1,
            {"5": {"object": operator_5, "quests": [quest_12]}, "6": {"object": operator_6, "quests": [quest_7]}},
        )

        response_quest_patch = self.client.patch(f"/quests/{quest_12.pk}/", data={"status": "3_sabotaged"})
        operators_2 = get_operators_with_quests(required_activity, ["1_created", "3_sabotaged"])

        self.assertEqual(response_quest_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(
            operators_2, {"5": {"object": operator_5, "quests": [quest_12]}, "6": {"object": operator_6, "quests": []}}
        )

        operator_5.readiness = "not_available"
        operator_5.save()
        quest_7.operator = operator_5
        quest_7.save()
        operators_3 = get_operators_with_quests(
            required_activity,
            ["1_created", "2_processing", "3_sabotaged", "4_expired", "5_cancelled", "6_success"],
            readiness=False,
        )
        quests_by_5 = set([quest.pk for quest in operators_3["5"].pop("quests")])
        operators_3["5"]["quests"] = quests_by_5

        self.assertEqual(
            operators_3,
            {
                "5": {"object": operator_5, "quests": {quest_12.pk, quest_7.pk}},
                "7": {"object": operator_7, "quests": []},
                "8": {"object": operator_8, "quests": []},
            },
        )
        self.assertEqual(
            get_operators_with_quests(
                activity=Activity.objects.get(name="Оператор ЧПУ"),
                quest_statuses=["1_created", "2_processing", "3_sabotaged", "4_expired", "5_cancelled", "6_success"],
            ),
            dict(),
        )

    def test_quest_update_time_out(self) -> None:
        """Ограничение на изменение задачи после того, как время на ее выполнение закончилось"""

        task = Quest.objects.get(title="Восстановить интернет")
        response = self.client.patch(f"/quests/{task.pk}/", data={"status": "6_success", "report": "Восстановлено"})
        updated_task = Quest.objects.get(title="Восстановить интернет")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual("Задача не может быть изменена, после истечения времени" in str(response.data), True)
        self.assertEqual(task.status, updated_task.status)
        self.assertEqual(task.report, updated_task.report)


class QuestTransferResponsibilityCase(APITestCase):
    """Тест разделения ответственности за выполнение большой задачи сотрудниками с одинаковой должностью"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "quests_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="8064AlAla551")
        self.client.force_authenticate(user=self.user)

    def test_quest_division(self) -> None:
        """Тест функции автоматического назначения исполнителя задачи"""

        parent_task = Quest.objects.create(
            title="Родительская задача",
            description="Родительское описание",
            creator=self.user,
            operator=Employee.objects.get(username="8068DaDa0b6d"),
            required=self.user.activity,
            dead_line="2026-09-12T15:21:54.527Z",
        )
        for i in range(1, 4):
            child_task_data = {
                "title": f"Подзадача №{i}",
                "description": "Описание",
                "related_quest": parent_task.pk,
                "required": self.user.activity.pk,
                "dead_line": f"2026-09-0{i}T15:21:54.527Z",
            }
            response = self.client.post("/quests/", data=child_task_data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        new_tasks = Quest.objects.filter(status="1_created", required=self.user.activity)
        self_user_tasks = Quest.objects.filter(operator__username="8064AlAla551", status="1_created")
        user_6_tasks = Quest.objects.filter(operator__username="8068DaDa0b6d", status="1_created")

        self.assertEqual((len(new_tasks), len(self_user_tasks), len(user_6_tasks)), (4, 1, 3))

    def test_quest_auto_sabotaged_status(self) -> None:
        """Создание задачи для несуществующего сотрудника"""

        sabotaged_task_data = {
            "title": "Задача",
            "description": "Задача для сотрудника, которого нет в организации",
            "required": Activity.objects.get(name="Оператор ЧПУ").pk,
            "dead_line": "2026-09-01T15:21:54.527Z",
        }
        sabotaged_response = self.client.post("/quests/", data=sabotaged_task_data)
        new_task = Quest.objects.get(title="Задача")

        self.assertEqual(sabotaged_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(new_task.status, "3_sabotaged")


class QuestCommonEmployeeTestCase(APITestCase):
    """Тесты запросов обычных пользователей, связанных с моделью Quest"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "quests_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="7750OlOl3545")
        self.client.force_authenticate(user=self.user)

    @freeze_time("2026-08-02T15:21:54.527Z")
    def test_common_employee_quests_getting(self) -> None:
        """Отображение обычному сотруднику только тех задач, в которых он является исполнителем или создателем"""

        response = self.client.get("/quests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(
            response.data,
            [
                {
                    "title": "Запустить производство",
                    "operator": "Олегов Олег Олегович",
                    "required_activity": "Инженер-наладчик",
                    "dead_line": "2026-09-01T06:59:59.999000+07:00",
                    "status": "2_processing",
                },
                {
                    "title": "Выдать комплектующие",
                    "operator": "Галинина Галина Галиновна",
                    "required_activity": "Кладовщик",
                    "dead_line": "2026-07-31T22:00:00+07:00",
                    "status": "6_success",
                },
                {
                    "title": "Подготовить место для сборки оборудования",
                    "operator": "Данилов Данил Данилович",
                    "required_activity": "Слесарь",
                    "dead_line": "2026-08-01T03:00:00+07:00",
                    "status": "6_success",
                },
            ],
        )

    def test_cyclic_dependence_exception(self) -> None:
        """Исключение циклической зависимости при замене задачи-родителя"""

        some_task = Quest.objects.get(title__startswith="Запустить")
        sub_task = Quest.objects.get(title__startswith="Нанять")
        sub_task.creator = self.user
        sub_task.save()
        cyclic_task = Quest.objects.create(
            title="Починить интернет",
            description="Сисадмин недоступен, товарищ инженер, выручайте",
            creator=Employee.objects.get(username="7748IrIrde5b"),
            related_quest=Quest.objects.get(title="Нужен еще один инженер"),
            dead_line="2026-07-31T16:11:10.1Z",
            required=Activity.objects.get(name="Инженер-наладчик"),
            operator=self.user,
            path_to_root="4/6/8/",
        )
        response_1 = self.client.patch(f"/quests/{some_task.pk}/", data={"status": "6_success"})
        response_2 = self.client.patch(f"/quests/{sub_task.pk}/", data={"related_quest": cyclic_task.pk})
        response_3 = self.client.patch(f"/quests/{some_task.pk}/", data={"related_quest": ""})
        response_4 = self.client.patch(f"/quests/{some_task.pk}/", data={"status": "5_cancelled"})

        self.assertEqual(response_1.status_code, status.HTTP_200_OK)
        self.assertEqual(some_task == some_task.related_quest, False)
        self.assertEqual(response_2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("Попытка установить циклическую зависимость" in str(response_2.data), True)
        self.assertEqual(response_3.status_code, status.HTTP_200_OK)
        self.assertEqual(response_4.status_code, status.HTTP_400_BAD_REQUEST)

        denied_delete = self.client.delete(f"/quests/{some_task.pk}/")
        failed_delete = self.client.delete(f"/quests/{sub_task.pk}/")

        self.assertEqual(denied_delete.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            "Удалять задачи может только суперпользователь или их создатель" in str(denied_delete.data), True
        )
        self.assertEqual(failed_delete.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("Удаление задачи запрещено, пока она имеет связанные подзадачи" in failed_delete.data, True)
