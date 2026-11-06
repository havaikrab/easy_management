import logging
from typing import Any

from django.conf import settings
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

        super_count = Employee.objects.filter(is_superuser=True).count()
        logger.warning("Количество супер-пользователей на момент запуска сервера: %d", super_count)

    def handle(self, *args: Any, **options: Any) -> None:
        """Вызов команды"""

        if settings.CREATE_SUPER_ADMIN:
            super_name = settings.SUPER_ADMIN_NAME
            if Employee.objects.filter(username=super_name).exists():
                logger.info("Супер-пользователь %s уже существует, создание пропущено", super_name)
            else:
                required = (
                    settings.SUPER_ADMIN_ACTIVITY,
                    super_name,
                    settings.SUPER_LAST_NAME,
                    settings.SUPER_FIRST_NAME,
                    settings.SUPER_PASSWORD,
                )
                if not all(required):
                    raise ValueError("Не указаны данные для создания супер-пользователя")
                activity, created = Activity.objects.get_or_create(
                    name=settings.SUPER_ADMIN_ACTIVITY,
                    defaults={
                        "description": f"Должность {settings.SUPER_ADMIN_ACTIVITY} "
                        f"создана автоматически для пользователя {super_name}",
                    },
                )
                if created:
                    logger.info(
                        "Зарегистрирована должность %s для нового супер-пользователя", settings.SUPER_ADMIN_ACTIVITY
                    )
                Employee.objects.create_superuser(
                    username=super_name,
                    last_name=settings.SUPER_LAST_NAME,
                    first_name=settings.SUPER_FIRST_NAME,
                    father_name=settings.SUPER_FATHER_NAME,
                    activity=activity,
                    password=settings.SUPER_PASSWORD,
                )
        self.__check_super_exists()
