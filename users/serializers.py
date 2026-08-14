from typing import Any, cast

from django.db import IntegrityError
from rest_framework import serializers

from management.models import Activity
from management.services import set_activity_relation

from .models import Employee
from .services import generate_username


class EmployeeRegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации нового сотрудника"""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        """Параметры сериализатора"""

        model = Employee
        fields = (
            "username",
            "last_name",
            "first_name",
            "father_name",
            "activity",
            "manager",
            "email",
            "readiness",
            "password",
            "password_confirm",
        )
        read_only_fields = ["username"]

    def validate(self, attrs: dict) -> Any:
        """Проверка совпадения передаваемых значений пароля"""

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Пароли не совпадают")
        attrs.pop("password_confirm")
        return super().validate(attrs)

    def create(self, validated_data: dict) -> Employee:
        """Создание объекта пользователя с хешированием пароля"""

        manager = validated_data.get("manager")
        new_employee_activity = validated_data.get("activity")
        if isinstance(manager, Employee) and isinstance(new_employee_activity, Activity):
            set_activity_relation(manager.activity, new_employee_activity)
        password = validated_data.pop("password")
        while True:
            try:
                username = generate_username(validated_data)
                return Employee.objects.create_user(username=username, password=password, **validated_data)
            except IntegrityError:
                continue


class EmployeeBaseSerializer(serializers.ModelSerializer):
    """Сериализатор отображения и изменения объекта сотрудника"""

    class Meta:
        """Параметры сериализатора"""

        model = Employee
        fields = (
            "username",
            "last_name",
            "first_name",
            "father_name",
            "activity",
            "manager",
            "email",
            "readiness",
        )
        read_only_fields = ["username"]

    def validate(self, attrs: dict) -> Any:
        """Исключение циклической субординации"""

        candidate = attrs.get("manager", None)
        instance = cast(Employee, self.instance)
        if isinstance(candidate, Employee):
            subordination_list = [instance]
            while candidate is not None:
                if candidate in subordination_list:
                    subordination_list.append(candidate)
                    chain = " --> ".join([employee.username for employee in subordination_list])
                    raise serializers.ValidationError(f"Циклическая субординация сотрудников недопустима: {chain}")
                subordination_list.append(candidate)
                next_manager = candidate.manager
                candidate = next_manager
        return super().validate(attrs)


class EmployeeChangePasswordSerializer(serializers.ModelSerializer):
    """Сериализатор обновления пароля от аккаунта"""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        """Параметры сериализатора"""

        model = Employee
        fields = ("current_password", "new_password", "new_password_confirm")

    def validate_current_password(self, value: str) -> None:
        """Проверка, знает ли пользователь текущий пароль"""

        user = cast(Employee, self.context.get("user"))
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")

    def validate(self, attrs: dict) -> Any:
        """Проверка совпадения передаваемых значений new_password и new_password_confirm"""

        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("Пароли не совпадают")
        return super().validate(attrs)

    def save(self, **kwargs: Any) -> Employee:
        """Сохранение нового пароля"""

        user = cast(Employee, self.context["user"])
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
