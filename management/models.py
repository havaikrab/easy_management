from django.db import models

from users.models import Employee


class Activity(models.Model):
    """Модель должности сотрудника"""

    name: models.CharField = models.CharField(unique=True, max_length=100, verbose_name="Название должности")
    description: models.TextField = models.TextField(verbose_name="Описание должности")

    class Meta:
        """Настройки отображения"""

        verbose_name = "Должность"
        verbose_name_plural = "Должности"
        ordering = ["name"]

    def __str__(self) -> str:
        """Строковое представление должности"""

        return str(self.name)


class Quest(models.Model):
    """Модель задачи"""

    title: models.CharField = models.CharField(max_length=200, verbose_name="Формулировка задачи")
    description: models.TextField = models.TextField(verbose_name="Описание задачи")
    creator: models.ForeignKey = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, related_name="commands", null=True, verbose_name="Заявитель"
    )
    related_quest: models.ForeignKey = models.ForeignKey(
        "self", on_delete=models.PROTECT, related_name="sub_quests", null=True, verbose_name="Задача-родитель"
    )
    operator: models.ForeignKey = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, related_name="tasks", null=True, verbose_name="Ответственный исполнитель"
    )
    required: models.ForeignKey = models.ForeignKey(
        Activity, on_delete=models.PROTECT, related_name="responsibilities", verbose_name="Ответственная должность"
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    dead_line: models.DateTimeField = models.DateTimeField(verbose_name="Назначенный срок")
    STATUS_CHOICES = [
        ("1_created", "Создана"),
        ("2_processing", "Обрабатывается"),
        ("3_sabotaged", "Выполнение прервано"),
        ("4_expired", "Просрочена"),
        ("5_cancelled", "Отменена"),
        ("6_success", "Успешно завершена"),
    ]
    status: models.CharField = models.CharField(
        max_length=12, choices=STATUS_CHOICES, verbose_name="Статус", default="1_created"
    )
    report: models.TextField = models.TextField(blank=True, default="", verbose_name="Отчет")
    path_to_root: models.TextField = models.TextField(verbose_name="Последовательность задач-родителей", db_index=True)

    class Meta:
        """Настройки отображения"""

        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = [
            "required",
            "status",
            "title",
        ]

    def __str__(self) -> str:
        """Строковое представление задачи"""

        return str(self.title)
