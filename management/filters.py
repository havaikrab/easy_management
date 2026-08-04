from typing import cast

from django.db.models import QuerySet
from django_filters.rest_framework import (
    BooleanFilter,
    CharFilter,
    FilterSet,
    NumberFilter,
    OrderingFilter,
)
from rest_framework.request import Request
