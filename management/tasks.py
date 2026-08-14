import logging

from celery import shared_task
from django.utils import timezone

from management.models import Quest

logger = logging.getLogger(__name__)


@shared_task
def check_dead_line_set_expired() -> None:
    """Проверяет наличие в базе данных наличие незавершенных задач и
    устанавливает статус "4_expired" для тех, у которых закончилось время на выполнение"""

    now = timezone.now()
    expired_quests = Quest.objects.filter(status__in=["1_created", "2_processing", "3_sabotaged"], dead_line__lt=now)
    updated_count = expired_quests.update(status="4_expired")
    logger.warning("Периодическая проверка выявила %d просроченных задач", updated_count)
