from django.contrib.auth.models import AbstractUser
from django.db import models


class Employee(AbstractUser):
    """Модель сотрудника"""

    username: models.CharField = models.CharField(unique=True, max_length=12, verbose_name="Уникальный идентификатор")
    last_name: models.CharField = models.CharField(max_length=100, verbose_name="Фамилия")
    first_name: models.CharField = models.CharField(max_length=100, verbose_name="Имя")
    father_name: models.CharField = models.CharField(blank=True, null=True, max_length=100, verbose_name="Отчество")
    activity: models.ForeignKey = models.ForeignKey(
        "management.Activity", on_delete=models.PROTECT, related_name="employees", verbose_name="Должность"
    )
    manager: models.ForeignKey = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="slaves", null=True, verbose_name="Руководитель"
    )
    STATUS_CHOICES = [
        ("ready_to_work", "Готов к работе"),
        ("not_available", "Не доступен"),
        ("automated", "Автоматизированный терминал"),
    ]
    readiness: models.CharField = models.CharField(
        max_length=13, choices=STATUS_CHOICES, verbose_name="Готовность к работе", default="Не доступен"
    )

    class Meta:
        """Настройки отображения"""

        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["activity", "last_name"]

    def __str__(self) -> str:
        """Строковое представление сотрудника"""

        return f"{self.last_name} {self.first_name}"
