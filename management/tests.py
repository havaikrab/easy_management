from rest_framework import status
from rest_framework.test import APITestCase

from users.models import Employee

from .models import Activity


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
