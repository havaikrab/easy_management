from django.contrib import admin

from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Класс представления модели сотрудника в админ-панели Django"""

    list_display = ("username", "last_name", "first_name", "father_name", "activity", "manager", "readiness")
    search_fields = ("last_name", "first_name", "activity")
    list_filter = ("activity", "manager", "readiness")
