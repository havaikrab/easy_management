from rest_framework import status
from rest_framework.test import APITestCase

from .models import Employee


class EmployeeTestCase(APITestCase):
    """Группа тестов для модели Employee"""

    fixtures = ["activities_fixture.json", "employees_fixture.json"]

    def setUp(self) -> None:
        """Предварительная авторизация пользователя"""

        self.user = Employee.objects.get(username="7748IrIrde5b")
        self.client.force_authenticate(user=self.user)

    def test_employee_create(self) -> None:
        """Устройство нового сотрудника в организацию"""

        self.assertEqual(len(Employee.objects.all()), 12)
        new_employee_data = {
            "last_name": "Аннова",
            "first_name": "Анна",
            "father_name": "Анновна",
            "activity": 4,
            "manager": 2,
            "password": "hard_to_remember",
            "password_confirm": "hard_to_remember",
        }
        response = self.client.post("/users/", new_employee_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(Employee.objects.all()), 13)
        username = response.data.pop("username")
        self.assertEqual(username[4:8], "AnAn")
        self.assertEqual(
            response.data,
            {
                "last_name": "Аннова",
                "first_name": "Анна",
                "father_name": "Анновна",
                "activity": 4,
                "manager": 2,
                "email": "",
                "readiness": "not_available",
            },
        )

    def test_getting_employee_list(self) -> None:
        """Просмотр списка сотрудников"""

        response = self.client.get("/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 10)

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
