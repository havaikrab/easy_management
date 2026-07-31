from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from .models import Activity, Quest
from .serializers import ActivitySerializer, QuestCreatingSerializer, QuestSerializer


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

    def get_serializer_class(self) -> type:
        """Определяет класс сериализатора в зависимости от
        совершаемого пользователем действия и его роли по отношению к задаче"""

        if self.action == "create":
            self.serializer_class = QuestCreatingSerializer
        else:
            self.serializer_class = QuestSerializer
        return self.serializer_class

    def perform_destroy(self, instance: Quest) -> None:
        """Исключает возможность удаления задачи, имеющей подзадачи"""

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Удаление задачи запрещено, пока она имеет связанные подзадачи")
