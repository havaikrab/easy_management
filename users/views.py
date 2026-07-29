from typing import Any

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Employee
from .serializers import (
    EmployeeBaseSerializer,
    EmployeeChangePasswordSerializer,
    EmployeeRegisterSerializer,
)


class EmployeeViewSet(ModelViewSet):
    """Вьюсет для модели сотрудника"""

    queryset = Employee.objects.all()

    def get_serializer_class(self) -> type:
        """Определяет класс сериализатора в зависимости от действия контроллера"""

        if self.action == "create":
            self.serializer_class = EmployeeRegisterSerializer
        else:
            self.serializer_class = EmployeeBaseSerializer

        return super().get_serializer_class()


class EmployeeChangePasswordAPIView(APIView):
    """Контроллер обновления пароля от аккаунта сотрудника"""

    serializer_class = EmployeeChangePasswordSerializer

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """PATCH-запрос на смену пароля"""

        serializer = EmployeeChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
