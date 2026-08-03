import logging
from typing import Any

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from management.models import Activity
from users.models import Employee

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """При запуске сервера проверяет наличие зарегистрированных супер-пользователей,
    создает нового супер-пользователя при наличии необходимых данных в переменных окружения"""

    @staticmethod
    def __check_super_exists() -> None:
        """Проверяет наличие зарегистрированных супер-пользователей"""

        super_count = len(Employee.objects.filter(is_superuser=True).all())
        logger.warning("Количество супер-пользователей на момент запуска сервера: %d", super_count)

    @staticmethod
    def __get_or_create_activity() -> Activity:
        """Получение из переменных окружения названия должности для нового-суперпользователя"""

        activity_name = settings.SUPER_ADMIN_ACTIVITY
        super_name = settings.SUPER_ADMIN_NAME
        if None in (activity_name, super_name):
            raise ValueError("Не указано имя нового супер-пользователя или название его должности")
        try:
            return Activity.objects.get(name=activity_name)
        except ObjectDoesNotExist:
            logger.info("Должность для нового супер-пользователя автоматически создана")
            return Activity.objects.create(
                name=activity_name,
                description=f"Должность {activity_name} создана автоматически для пользователя {super_name}",
            )

    def handle(self, *args: Any, **options: Any) -> None:
        """Вызов команды"""

        if settings.CREATE_SUPER_ADMIN:
            super_name = settings.SUPER_ADMIN_NAME
            try:
                Employee.objects.get(username=super_name)
                logger.error(
                    "Пользователь с username %s уже существует в базе данных и не может быть создан повторно",
                    super_name,
                )
                raise ValueError("Попытка создать существующий объект пользователя повторно")
            except ObjectDoesNotExist:
                activity = self.__get_or_create_activity()
                super_last_name = settings.SUPER_LAST_NAME
                super_first_name = settings.SUPER_FIRST_NAME
                super_father_name = settings.SUPER_FATHER_NAME
                super_password = settings.SUPER_PASSWORD
                if None in (super_last_name, super_first_name, super_password):
                    raise ValueError("Не указаны имя, фамилия или пароль нового супер-пользователя")
                Employee.objects.create_superuser(
                    username=super_name,
                    last_name=super_last_name,
                    first_name=super_first_name,
                    father_name=super_father_name,
                    activity=activity,
                    password=super_password,
                )
        self.__check_super_exists()
