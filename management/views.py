from typing import Any, Sequence, cast

from django.db.models import ProtectedError, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from users.models import Employee

from .filters import QuestFilterSet
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


@extend_schema_view(
    create=extend_schema(
        summary="Создание новой должности",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "add_activity" или статуса супер-пользователя.
В теле запроса обязательно передаются ключи "name" и "description", все значения "name" должны быть уникальными.
""",
    ),
    list=extend_schema(
        summary="Отображение списка должностей",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "view_activity" или статуса супер-пользователя.
В запросе могут передаваться параметры для поиска объектов с указанием подстроки,
входящей в название или описание должности
""",
    ),
    retrieve=extend_schema(
        summary="Отображение должности",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "view_activity" или статуса супер-пользователя.
""",
    ),
    update=extend_schema(
        summary="Полное обновление должности",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "add_activity" или статуса супер-пользователя.
В теле запроса необходимо передать обязательные ключи "name" и "description" с соответствующими значениями.
""",
    ),
    partial_update=extend_schema(
        summary="Частичное обновление должности",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "add_activity" или статуса супер-пользователя.
В теле запроса нужно указать новые значения для одного или нескольких полей "name", "description" или "partners".
""",
    ),
    destroy=extend_schema(
        summary="Удаление должности",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "add_activity" или статуса супер-пользователя.
Удаление должности невозможно, пока в БД существуют объекты пользователей, имеющие связь с этой должностью
""",
    ),
)
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


@extend_schema_view(
    create=extend_schema(
        summary="Создание новой задачи",
        description="""
Необходима авторизация. В запросе передаются значения для соответствующих полей. Модель задачи имеет следующие поля:
- "title" - название задачи. Обязательное поле. Максимальная длина строки 200 символов.
- "description" - описание задачи. Обязательное поле. Текст неограниченной длины.
- "creator" -  создатель задачи. Устанавливается автоматически, является внешним ключом на объект пользователя.
- "related_quest" - зависимая, или задача-родитель. Необязательное поле. Внешний ключ на объект другой задачи.
    Задачей-родителем может быть указана только та, у которой пользователь является создателем или исполнителем.
- "operator" - исполнитель. Необязательное поле. Внешний ключ на объект пользователя-исполнителя задачи.
    Исполнителем может быть указан пользователь, имеющий должность являющуюся "партнерской" с должностью создателя.
- "required" - должность исполнителя. Обязательное поле. Внешний ключ на объект должности.
- "created_at" - дата создания. Устанавливается автоматически. Строка даты-времени формата ISO 8601.
- "dead_line" - срок выполнения. Обязательное поле. Строка даты-времени формата ISO 8601. При наличии у задачи
    родительской задачи значение "dead_line" не должно превышать соответствующее значение родительской задачи.
- "status" - статус стадии выполнения задачи. При создании автоматически устанавливается значение "1_created".
- "report" - отчет о выполнении задачи. При создании автоматически устанавливается пустая строка.
- "path_to_root" - путь к главной родительской задаче. Вычисляется автоматически при передаче ключа "related_quest".
""",
    ),
    list=extend_schema(
        summary="Отображение списка задач",
        description="""
Необходима авторизация. Пользователям имеющим статус супер-пользователя доступен весь список объектов задач.
Для рядового пользователя, при отсутствии дополнительных параметров запроса выводится список задач,
в которых он указан владельцем или исполнителем. Эндпоинт возвращает сокращенную характеристику объектов.
Дополнительные параметры запросов:
- "search=value" - регистронезависимый поиск задач, в названии или описании которых содержится строка value.
- "title__icontains=value" - регистронезависимый поиск задач, в названии которых содержится строка value.
- "description__icontains=value" - регистронезависимый поиск задач, в описании которых содержится строка value.
- "creator=value" - поиск задач, создателем которых является пользователь с id=value.
- "creator__in=value" - поиск задач, созданных пользователями, id которых указаны в value.
- "related_quest=value" - поиск задач, родительской для которых, является задача с id=value.
- "operator=value" - поиск задач, исполнителем которых является пользователь с id=value.
- "operator__in=value" - поиск задач, исполнителями которых являются пользователями, с id указанными в value.
- "required=value" - поиск задач для должности с id=value.
- "created_at=value" - поиск задач, созданных в указанное время value.
- "created_at__gt=value" - поиск задач, созданных после указанного момента времени value.
- "created_at__lt=value" - поиск задач, созданных до указанного момента времени value.
- "dead_line=value" - поиск задач, требуемый срок завершения которых равен значению времени value.
- "dead_line__gt=value" - поиск задач, указанный срок завершения которых наступит после момента времени value.
- "dead_line__lt=value" - поиск задач, указанный срок завершения которых наступит до момента времени value.
- "status=value" - поиск задач с точным указание статуса value.
- "page=value" - порядковый номер страницы отображения задач.
- "page_size=value" - количество задач, отображаемых на одной странице, стандартное значение - 10, максимальное - 20.
- Возможные значения статусов: "1_created" - "Создана", "2_processing" - "Обрабатывается", "3_sabotaged" -
    "Выполнение прервано", "4_expired" - "Просрочена", "5_cancelled" - "Отменена", "6_success" - "Успешно завершена".
- Поля "id", "created_at", "dead_line", "status" также используются с параметром "ordering" для указания
    порядка и направления сортировки.
""",
    ),
    retrieve=extend_schema(
        summary="Отображение задачи",
        description="""
Необходима авторизация. Для отображения доступны только те задачи,
у которых пользователь является исполнителем или создателем.""",
    ),
    update=extend_schema(
        summary="Полное обновление задачи",
        description="""
Необходима авторизация. Пользователю, являющемуся создателем задачи, в теле запроса необходимо передать
все ключи для обязательных полей. Список обязательных полей приведен в документации по созданию объектов задач.
Пользователь-исполнитель может передавать значения только для полей "report" и "status".
Статус "4_expired" - не может быть указан пользователем, этот статус устанавливается автоматически при
истечении срока, отведенного на выполнение задачи.
""",
    ),
    partial_update=extend_schema(
        summary="Частичное обновление задачи",
        description="""
Необходима авторизация. В теле запроса нужно указать новые значения для одного или нескольких полей объекта задачи.
Ограничения для передаваемых значений указаны в документации по полному обновлению объекта задачи.
""",
    ),
    destroy=extend_schema(
        summary="Удаление задачи",
        description="""
Необходима авторизация. Задачи могут удалять только их создатели или пользователи, имеющие статус супер-пользователя.
Удаление задачи невозможно, пока она является родительской для одной или нескольких других задач.
""",
    ),
)
class QuestViewSet(ModelViewSet):
    """Вьюсет для модели задачи"""

    queryset = Quest.objects.all()
    pagination_class = QuestPaginator
    filterset_class = QuestFilterSet
    ordering_fields = ["id", "created_at", "dead_line", "status"]

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


@method_decorator(
    name="post",
    decorator=extend_schema(
        summary="Создание связей между должностями",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "add_activity" или статуса супер-пользователя.
Пользователь имеющий доступ к контроллеру может налаживать связи между должностями. Сотрудники, чьи должности имеют
связь могут создавать друг для друга задачи. При регистрации нового пользователя проверяется наличие связи между его
должностью и должностью его руководителя. При отсутствии такой связи, она создается автоматически.
ID связываемых должностей передаются в адресной строке, тело запроса не содержит дополнительных данных.
""",
        responses={
            200: OpenApiResponse(description="Связь создана"),
            401: OpenApiResponse(description="Пользователь не авторизован"),
            400: OpenApiResponse(description="Связь между должностями уже существует"),
            403: OpenApiResponse(description="У пользователя отсутствуют необходимые права"),
            404: OpenApiResponse(
                description="Одна или обе должности не существуют",
            ),
        },
    ),
)
@method_decorator(
    name="delete",
    decorator=extend_schema(
        summary="Удаление связей между должностями",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "add_activity" или статуса супер-пользователя.
Пользователь имеющий доступ к контроллеру может разрывать связи между должностями. Сотрудники, чьи должности не имеют
связи, не могут создавать друг для друга задачи. ID должностей передаются в адресной строке,
тело запроса не содержит дополнительных данных.
""",
        responses={
            200: OpenApiResponse(description="Связь удалена"),
            401: OpenApiResponse(description="Пользователь не авторизован"),
            400: OpenApiResponse(description="Связи между должностями не существует"),
            403: OpenApiResponse(description="У пользователя отсутствуют необходимые права"),
            404: OpenApiResponse(
                description="Одна или обе должности не существуют",
            ),
        },
    ),
)
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


@method_decorator(
    name="get",
    decorator=extend_schema(
        summary="Получение структуры подзадач",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "view_quest" или статуса супер-пользователя.
Пользователь имеющий доступ к контроллеру получает возможность изучать структуру постановки и взаимосвязи задач,
от которых зависит выполнение основной задачи. Каждый "узел" возвращаемой структуры содержит
детальную информацию о конкретной подзадаче.
""",
        responses={
            200: OpenApiResponse(description="json-структура зависимостей задач"),
            401: OpenApiResponse(description="Пользователь не авторизован"),
            403: OpenApiResponse(description="У пользователя отсутствуют необходимые права"),
            404: OpenApiResponse(
                description="Главная задача не найдена",
            ),
        },
    ),
)
class QuestGetTreeView(APIView):
    """Контроллер отображения структуры подзадач"""

    permission_classes = [IsAuthenticated, IsQuestAnalyst]

    def get(self, request: Request, pk: int, *args: Any, **kwargs: Any) -> Response:
        """Отображает "дерево подзадач" для выбранной задачи"""

        quest = get_object_or_404(Quest, pk=pk)
        return Response({"tree": get_sub_quests_map(quest)})
