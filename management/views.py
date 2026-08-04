from typing import Any, Sequence, cast

from django.db.models import ProtectedError, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from users.models import Employee

from .models import Activity, Quest
from .paginators import QuestPaginator
from .permissions import IsActivityConstructor, IsActivityUser, IsQuestAnalyst
from .serializers import (
    ActivitySerializer,
    QuestCreatingSerializer,
    QuestSerializer,
    QuestSimplifiedSerializer,
    QuestUpdateReportSerializer,
)
from .services import get_sub_quests_map


class ActivityViewSet(ModelViewSet):
    """Вьюсет для модели должности"""

    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    search_fields = ["name", "description"]

    def get_permissions(self) -> Sequence:
        """Ограничение прав использования контроллера"""

        if self.action in ["list", "retrieve"]:
            self.permission_classes = [IsAuthenticated, IsActivityUser]
        else:
            self.permission_classes = [IsAuthenticated, IsActivityConstructor]
        return super().get_permissions()

    def perform_destroy(self, instance: Activity) -> None:
        """Проверка на наличие имеющихся связанных объектов других моделей"""

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("Удаление выбранной должности невозможно, это вызовет повреждение структуры данных")


class QuestViewSet(ModelViewSet):
    """Вьюсет для модели задачи"""

    queryset = Quest.objects.all()
    pagination_class = QuestPaginator

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


class ManageActivityRelationsView(APIView):
    """Контроллер управления связями между должностями"""

    permission_classes = [IsAuthenticated, IsActivityConstructor]

    def post(self, request: Request, activity_pk: int, partner_pk: int, *args: Any, **kwargs: Any) -> Response:
        """Устанавливает взаимосвязь между двумя должностями"""

        activity = get_object_or_404(Activity, pk=activity_pk)
        partner = get_object_or_404(Activity, pk=partner_pk)
        if activity.partners.filter(pk=partner_pk).exists():
            return Response({"error": "Связь между должностями уже существует"}, status=status.HTTP_400_BAD_REQUEST)
        activity.partners.add(partner)
        return Response({"message": f"Установлена связь между должностями {activity.name} и {partner.name}."})

    def delete(self, request: Request, activity_pk: int, partner_pk: int, *args: Any, **kwargs: Any) -> Response:
        """Ограничивает взаимосвязь между двумя должностями"""

        activity = get_object_or_404(Activity, pk=activity_pk)
        partner = get_object_or_404(Activity, pk=partner_pk)
        if not activity.partners.filter(pk=partner_pk).exists():
            return Response({"error": "Связь между должностями не существует"}, status=status.HTTP_400_BAD_REQUEST)
        activity.partners.remove(partner)
        return Response({"message": f"Связь между должностями {activity.name} и {partner.name} исключена."})


class QuestGetTreeView(APIView):
    """Контроллер отображения структуры подзадач"""

    permission_classes = [IsAuthenticated, IsQuestAnalyst]

    def get(self, request: Request, pk: int, *args: Any, **kwargs: Any) -> Response:
        """Отображает "дерево подзадач" для выбранной задачи"""

        quest = get_object_or_404(Quest, pk=pk)
        return Response({"tree": get_sub_quests_map(quest)})
