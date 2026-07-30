from django.db.models import ProtectedError
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from .models import Activity
from .serializers import ActivitySerializer


class ActivityViewSet(ModelViewSet):
    """Вьюсет для модели должности"""

    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer

    def perform_destroy(self, instance: Activity) -> None:
        """Проверка на наличие имеющихся связанных объектов других моделей"""

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Удаление должности невозможно, это повлечет повреждение структуры данных")
