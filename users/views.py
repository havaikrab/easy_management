from typing import Any, Sequence, cast

from django.db.models import ProtectedError, Q, QuerySet
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from management.permissions import IsActivityUser

from .models import Employee
from .serializers import EmployeeBaseSerializer, EmployeeChangePasswordSerializer, EmployeeRegisterSerializer


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


class EmployeeChangePasswordAPIView(APIView):
    """Контроллер обновления пароля от аккаунта сотрудника"""

    serializer_class = EmployeeChangePasswordSerializer

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """PATCH-запрос на смену пароля"""

        serializer = EmployeeChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
