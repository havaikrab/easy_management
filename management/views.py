from typing import cast

from django.db.models import ProtectedError, Q, QuerySet
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.viewsets import ModelViewSet

from users.models import Employee

from .models import Activity, Quest
from .serializers import (
    ActivitySerializer,
    QuestCreatingSerializer,
    QuestSerializer,
    QuestSimplifiedSerializer,
    QuestUpdateReportSerializer,
)


class ActivityViewSet(ModelViewSet):
    """Вьюсет для модели должности"""

    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer

    def perform_destroy(self, instance: Activity) -> None:
        """Проверка на наличие имеющихся связанных объектов других моделей"""

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Удаление выбранной должности невозможно, это вызовет повреждение структуры данных")


class QuestViewSet(ModelViewSet):
    """Вьюсет для модели задачи"""

    queryset = Quest.objects.all()

    def get_queryset(self) -> QuerySet:
        """Ограничение набора отображаемых задач"""

        user = cast(Employee, self.request.user)
        if user.is_superuser:
            return Quest.objects.all()
        return Quest.objects.filter(Q(operator=user) | Q(creator=user))

    def get_serializer_class(self) -> type:
        """Определяет класс сериализатора в зависимости от
        совершаемого пользователем действия и его роли по отношению к задаче"""

        if self.action == "create":
            self.serializer_class = QuestCreatingSerializer
        elif self.action == "list":
            self.serializer_class = QuestSimplifiedSerializer
        elif self.action in ["update", "partial_update"]:
            quest = self.get_object()
            if quest.dead_line < timezone.now():
                raise PermissionDenied(
                    "Задача не может быть изменена, после истечения времени, отведенного на ее выполнение"
                )
            user = self.request.user
            if quest.creator == user:
                self.serializer_class = QuestSerializer
            else:
                if quest.operator == user:
                    self.serializer_class = QuestUpdateReportSerializer
                else:
                    raise PermissionDenied("Для изменения объекта задачи нужно быть ее создателем или исполнителем")
        else:
            self.serializer_class = QuestSerializer
        return self.serializer_class

    def perform_destroy(self, instance: Quest) -> None:
        """Исключает возможность удаления задачи, имеющей подзадачи"""

        quest = self.get_object()
        user = cast(Employee, self.request.user)
        if not user.is_superuser and quest.creator != user:
            raise PermissionDenied("Удалять задачи может только суперпользователь или их создатель")
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Удаление задачи запрещено, пока она имеет связанные подзадачи")
