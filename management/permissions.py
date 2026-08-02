from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from users.models import Employee


class IsActivityConstructor(BasePermission):
    """Определяет право создавать объекты должности"""

    message = "Доступ ограничен. Необходимы права создателя должностей"

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Проверка, имеет ли пользователь право создавать объекты модели Activity"""

        user = request.user
        if isinstance(user, Employee):
            return user.has_perms(["management.add_activity", "management.view_activity"]) or user.is_superuser
        return False


class IsActivityUser(BasePermission):
    """Определяет право использования объектов должности"""

    message = "Доступ ограничен. Необходимы права обращения с объектами должностей"

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Проверка, имеет ли пользователь право оперировать объектами модели Activity"""

        user = request.user
        if isinstance(user, Employee):
            return user.has_perm("management.view_activity") or user.is_superuser
        return False
