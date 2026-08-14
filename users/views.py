from typing import Any, Sequence, cast

from django.db.models import ProtectedError, Q, QuerySet
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from management.models import Activity
from management.permissions import IsActivityUser

from .models import Employee
from .serializers import (
    EmployeeBaseSerializer,
    EmployeeChangePasswordSerializer,
    EmployeeRegisterSerializer,
)
from .services import get_sorted_range_from_activ_operators


@extend_schema_view(
    create=extend_schema(
        summary="Создание учетной записи пользователя",
        description="""
Необходима авторизация, и обязательное наличие у пользователя права "view_activity" или статуса супер-пользователя.
Приложение предназначено для использования ограниченным кругом лиц, а именно только сотрудниками организации.
Таким образом, только высший руководитель или сотрудник "отдела кадров" должен быть наделен правом создавать
новые учетные записи пользователей, как правило при, устройстве на работу в данную организацию.
В запросе на создание объекта передаются значения для полей модели:
- "username" - идентификатор пользователя. Устанавливается автоматически при создании объекта.
- "last_name" - фамилия. Обязательное поле. Строка длиной не более ста символов.
- "first_name" - имя. Обязательное поле. Строка длиной не более ста символов.
- "father_name" - отчество. Необязательное поле. Строка длиной не более ста символов.
- "activity" - должность. Обязательное поле. Внешний ключ на объект должности.
- "manager" - руководитель. Обязательное поле. Внешний ключ на объект пользователя-руководителя.
- При регистрации нового пользователя проверяется наличие связи между его должностью и должностью его руководителя.
При отсутствии такой связи, она создается автоматически. Пользователь может не иметь руководителя только в том случае,
если он регистрируется через админ-панель, как правило такой пользователь является руководителем организации или
системным администратором, имеющим статус супер-пользователя.
- "readiness" - статус готовности к работе. При создании объекта автоматически присваивается значение "ready_to_work".
- "password" - пароль. Обязательное поле.
- "password_confirm" - подтверждение пароля. Обязательное поле. Для успешной регистрации, значения "password" и
"password_confirm" должны совпадать.
""",
    ),
    list=extend_schema(
        summary="Отображение списка сотрудников",
        description="""
Необходима авторизация. Пользователям обладающим правом "view_activity" или имеющим статус супер-пользователя
доступен для отображения весь список сотрудников организации. Остальным пользователям доступны объекты только тех
сотрудников, у которых должности имеют связь или совпадают с должностью авторизованного пользователя.
Пользователи, имеющие значение "readiness"-статуса равное "automated", отображаются только для супер-пользователей
или пользователей имеющих право "view_activity". Как правило эти объекты являются автоматизированными
системами, как например чат-боты или терминалы для массовой обработки и агрегации задач, исходящих от потребителей
услуг или продукции организации.
""",
    ),
    retrieve=extend_schema(
        summary="Отображение объекта сотрудника",
        description="""
Необходима авторизация. Авторизованному пользователю доступна полная информация о его учетных данных,
поле "password" не отображается из соображений безопасности.
""",
    ),
    update=extend_schema(
        summary="Полное обновление аккаунта пользователя",
        description="""
Необходима авторизация, статус супер-пользователя или наличие права "view_activity".
В теле запроса необходимо передать значения для обязательных полей объекта. Поле "username" остается неизменяемым
на всем протяжении существования учетной записи. По сравнению с эндпоинтом создания учетной
записи появляется возможность установить "readiness"-статус, что полезно, если по каким то причинам пользователь
не способен в данный момент выполнять поставленные задачи.
""",
    ),
    partial_update=extend_schema(
        summary="Частичное обновление аккаунта пользователя",
        description="""
Необходима авторизация, статус супер-пользователя или наличие права "view_activity".
В теле запроса нужно указать новые значения для одного или нескольких полей объекта.
""",
    ),
    destroy=extend_schema(
        summary="Удаление учетной записи пользователя",
        description="""
Необходима авторизация, статус супер-пользователя или наличие права "view_activity".
Объект сотрудника не может быть удален, пока в базе данных существуют другие объекты, у которых удаляемый пользователь
указан в качестве руководителя.
""",
    ),
)
class EmployeeViewSet(ModelViewSet):
    """Вьюсет для модели сотрудника"""

    queryset = Employee.objects.all()

    def get_queryset(self) -> QuerySet:
        """Определяет список доступных для отображения сотрудников"""

        user = cast(Employee, self.request.user)
        if user.is_superuser or user.has_perm("management.view_activity"):
            return Employee.objects.all()
        else:
            close_activities = user.activity.partners.all()
            return Employee.objects.filter(Q(activity__in=close_activities) | Q(activity=user.activity)).exclude(
                readiness="automated"
            )

    def get_permissions(self) -> Sequence:
        """Ограничивает круг пользователей, способных создавать новые учетные записи пользователей"""

        if self.action in ["list", "retrieve"]:
            self.permission_classes = [IsAuthenticated]
        else:
            self.permission_classes = [IsAuthenticated, IsActivityUser]
        return super().get_permissions()

    def get_serializer_class(self) -> type:
        """Определяет класс сериализатора в зависимости от действия контроллера"""

        if self.action == "create":
            self.serializer_class = EmployeeRegisterSerializer
        else:
            self.serializer_class = EmployeeBaseSerializer

        return super().get_serializer_class()

    def perform_destroy(self, instance: Employee) -> None:
        """Исключает возможность удаления сотрудника, являющегося руководителем для другого сотрудника"""

        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                "Удаление аккаунта сотрудника запрещено, пока он является руководителем для других сотрудников"
            )


@method_decorator(
    name="patch",
    decorator=extend_schema(
        summary="Смена пароля от аккаунта",
        responses={
            204: OpenApiResponse(description='При удачной смене возвращается "пустой" объект response.'),
            400: OpenApiResponse(description="""
- Неверный текущий пароль.
- Новый пароль не подтвержден.
"""),
            401: OpenApiResponse(description="Пользователь не авторизован."),
        },
    ),
)
class EmployeeChangePasswordAPIView(APIView):
    """Контроллер обновления пароля от аккаунта сотрудника"""

    permission_classes = [IsAuthenticated]
    serializer_class = EmployeeChangePasswordSerializer

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """PATCH-запрос на смену пароля"""

        serializer = EmployeeChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(
    name="get",
    decorator=extend_schema(
        summary="Получение потенциальных операторов для выполнения задачи",
        description="""
Эндпоинт возвращает список сотрудников с требуемой должностью и "readiness"-статусом равным "ready_to_work".
Список отсортирован по количеству активных задач у соответствующего сотрудника,
направление сортировки задается параметром "reverse" через адресную строку.
Каждый элемент списка также включает список с краткими характеристиками активных задач пользователя.
""",
        responses={
            200: OpenApiResponse(description='JSON-структура "список словарей" с данными сотрудников.'),
            401: OpenApiResponse(description="Пользователь не авторизован."),
            403: OpenApiResponse(description="Должность сотрудника и запрашиваемая должность не имеют связи."),
            404: OpenApiResponse(description="Запрашиваемая должность не найдена."),
        },
    ),
)
class CandidatesListView(APIView):
    """Контроллер, отображающий отсортированный по количеству активных задач
    список сотрудников определенной должности"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, activity_pk: int, *args: Any, **kwargs: Any) -> Response:
        """GET-запрос на отображение списка сотрудников"""

        user = cast(Employee, request.user)
        required_activity = get_object_or_404(Activity, pk=activity_pk)
        if not user.activity.partners.filter(pk=activity_pk).exists():
            raise PermissionDenied("Отсутствует право получения информации о сотрудниках c указанной должностью")
        reverse = request.query_params.get("reverse", "false").lower() == "true"
        data = get_sorted_range_from_activ_operators(required_activity, reverse=reverse)
        return Response(data)
