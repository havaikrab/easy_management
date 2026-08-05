from django.core.management import call_command
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from management.models import Activity, Quest

from .models import Employee


class EmployeeTestCase(APITestCase):
    """Группа тестов для модели Employee"""

    fixtures = ["activities_fixture.json", "employees_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="8024IvIvc0e0")
        self.client.force_authenticate(user=self.user)

    def test_employee_create(self) -> None:
        """Устройство нового сотрудника в организацию"""

        activity = Activity.objects.get(name="Бухгалтер")
        activity_relations_count = len(activity.partners.all())
        new_employee_data = {
            "last_name": "Аннова",
            "first_name": "Анна",
            "father_name": "Анновна",
            "activity": 4,
            "manager": 1,
            "password": "hard_to_remember",
            "password_confirm": "hard_to_remember",
        }

        self.assertEqual(len(Employee.objects.all()), 12)
        self.assertEqual(activity_relations_count, 4)

        response = self.client.post("/users/", new_employee_data)
        username = response.data.pop("username")
        updated_activity = Activity.objects.get(name="Бухгалтер")
        updated_activity_relations_count = len(updated_activity.partners.all())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(Employee.objects.all()), 13)
        self.assertEqual(updated_activity_relations_count, 5)
        self.assertEqual(username[4:8], "AnAn")
        self.assertEqual(
            response.data,
            {
                "last_name": "Аннова",
                "first_name": "Анна",
                "father_name": "Анновна",
                "activity": 4,
                "manager": 1,
                "email": "",
                "readiness": "ready_to_work",
            },
        )

    def test_getting_employee_list(self) -> None:
        """Просмотр списка сотрудников"""

        response = self.client.get("/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 12)

    def test_getting_employee_detail(self) -> None:
        """Просмотр информации о сотруднике"""

        response = self.client.get("/users/7/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "username": "8024IvIvhds0",
                "last_name": "Иванов",
                "first_name": "Иван",
                "father_name": "Иванович",
                "activity": 8,
                "manager": 4,
                "email": "",
                "readiness": "not_available",
            },
        )

    def test_employee_updating(self) -> None:
        """Перевод сотрудника в другую должность"""

        response = self.client.patch("/users/7/", data={"activity": 12})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "username": "8024IvIvhds0",
                "last_name": "Иванов",
                "first_name": "Иван",
                "father_name": "Иванович",
                "activity": 12,
                "manager": 4,
                "email": "",
                "readiness": "not_available",
            },
        )

    def test_employee_delete(self) -> None:
        """Увольнение сотрудника"""

        response = self.client.delete("/users/7/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(Employee.objects.all()), 11)

    def test_employee_failed_delete(self) -> None:
        """Неудачная попытка уволить сотрудника, имеющего подчиненных"""

        response = self.client.delete("/users/4/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_change_password(self) -> None:
        """Смена пароля пользователя"""

        current_password = self.user.password
        password_data = {
            "current_password": "12qaw34esz",
            "new_password": "zse43waq21",
            "new_password_confirm": "zse43waq21",
        }
        response = self.client.patch("/users/change_password/", password_data)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(current_password == self.user.password, False)

    def test_employee_failed_manager_change(self) -> None:
        """Отказ в назначении сотрудника руководителем для собственного руководителя"""

        response = self.client.patch("/users/4/", data={"manager": 10})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual("7750OlOl3545 --> 7950OlOli2bA --> 7750OlOl3545" in str(response.data), True)


class EmployeeSpecialTestCase(APITestCase):
    """Группа специфичных тестов для модели Employee"""

    fixtures = ["activities_fixture.json", "employees_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="8068DaDa0b6d")
        self.client.force_authenticate(user=self.user)

    def test_getting_employees_list_by_common_user(self) -> None:
        """Отображение списка коллег пользователю, не имеющему специальных прав"""

        response = self.client.get("/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 7)


class CreateSuperUserTestCase(APITestCase):
    """Тестирование кастомной команды set_super_user"""

    fixtures = ["activities_fixture.json", "employees_fixture.json"]

    @override_settings(CREATE_SUPER_ADMIN=False)
    def test_not_creating_super_user(self) -> None:
        """Вызов команды с флагом CREATE_SUPER_ADMIN=False"""

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)

        call_command("set_super_user")

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)

    @override_settings(CREATE_SUPER_ADMIN=True, SUPER_ADMIN_NAME=None)
    def test_invalid_call(self) -> None:
        """Вызов команды без передачи обязательных аргументов"""

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)

        with self.assertRaises(ValueError):
            call_command("set_super_user")

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)

    @override_settings(
        CREATE_SUPER_ADMIN=True,
        SUPER_ADMIN_ACTIVITY="Системный администратор",
        SUPER_ADMIN_NAME="7745AlAl2aec",
        SUPER_LAST_NAME="Михайлов",
        SUPER_FIRST_NAME="Михаил",
        SUPER_PASSWORD="МихалМихалыч",
    )
    def test_repeated_creating_super_user(self) -> None:
        """Попытка создать нового супер-пользователя с неуникальным идентификатором"""

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)

        with self.assertRaises(ValueError):
            call_command("set_super_user")

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)

    @override_settings(
        CREATE_SUPER_ADMIN=True,
        SUPER_ADMIN_ACTIVITY="Системный администратор",
        SUPER_ADMIN_NAME="super_admin",
        SUPER_LAST_NAME="Михайлов",
        SUPER_FIRST_NAME="Михаил",
        SUPER_PASSWORD="МихалМихалыч",
    )
    def test_success_creating_super_user(self) -> None:
        """Успешное создание супер-пользователя с существующей должностью"""

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)
        self.assertEqual(len(Activity.objects.all()), 12)
        self.assertEqual(
            Activity.objects.get(name="Системный администратор").description,
            "Ответственный за поддержание программного обеспечения организации в исправном состоянии",
        )

        call_command("set_super_user")

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 3)
        self.assertEqual(len(Activity.objects.all()), 12)
        self.assertEqual(
            Activity.objects.get(name="Системный администратор").description,
            "Ответственный за поддержание программного обеспечения организации в исправном состоянии",
        )

    @override_settings(
        CREATE_SUPER_ADMIN=True,
        SUPER_ADMIN_ACTIVITY="Временный админ",
        SUPER_ADMIN_NAME="super_admin",
        SUPER_LAST_NAME="Михайлов",
        SUPER_FIRST_NAME="Михаил",
        SUPER_PASSWORD="МихалМихалыч",
    )
    def test_success_creating_super_user_with_new_activity(self) -> None:
        """Успешное создание супер-пользователя с новой должностью"""

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 2)
        self.assertEqual(len(Activity.objects.all()), 12)

        call_command("set_super_user")

        self.assertEqual(len(Employee.objects.filter(is_superuser=True)), 3)
        self.assertEqual(len(Activity.objects.all()), 13)
        self.assertEqual(
            Activity.objects.get(name="Временный админ").description,
            "Должность Временный админ создана автоматически для пользователя super_admin",
        )


class GetActiveOperatorsTestCase(APITestCase):
    """Получение списка сотрудников, отсортированного по количеству их активных задач"""

    fixtures = ["activities_fixture.json", "employees_fixture.json", "quests_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="7750OlOl3545")
        self.client.force_authenticate(user=self.user)

    def test_getting_candidates(self) -> None:
        """Получение отсортированного списка сотрудников, определенной должности"""

        quests = Quest.objects.all()
        operator_5 = Employee.objects.get(username="8064AlAla551")
        operator_6 = Employee.objects.get(username="8068DaDa0b6d")
        creator = Employee.objects.get(username="7750OlOl3545")
        required_activity = Activity.objects.get(name="Слесарь")
        for i in quests:
            if len(i.title) % 2 == 0:
                i.operator = operator_5
            else:
                i.operator = operator_6
            if i.status == "4_expired":
                i.status = "1_created"
            i.creator = creator
            i.required = required_activity
            i.save()
        response = self.client.get(f"/users/candidates/{required_activity.pk}/")
        response_reverse = self.client.get(f"/users/candidates/{required_activity.pk}/?reverse=TRUE")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response_reverse.status_code, status.HTTP_200_OK)
        self.assertEqual((len(response.data), len(response_reverse.data)), (2, 2))
        self.assertEqual(response.data[0]["operator"]["username"], operator_6.username)
        self.assertEqual(len(response.data[0]["quests"]), 2)
        self.assertEqual(response_reverse.data[0]["operator"]["username"], operator_5.username)
        self.assertEqual(len(response_reverse.data[0]["quests"]), 3)
