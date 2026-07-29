import secrets
from time import time

from unidecode import unidecode


def generate_username(data: dict) -> str:
    """Генерирует уникальный идентификатор пользователя для поля username"""

    second = str(int(time()))[-4:]
    initials = f'{data['last_name'][:2]}{data["first_name"][:2]}'
    secret = secrets.token_hex(2)
    return unidecode(second + initials + secret)
