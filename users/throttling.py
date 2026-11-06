from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Ограничение частоты запросов на вход в систему с одного IP-адреса, защищает от перебора паролей.
    Лимит задается в настройках REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"]"""

    scope = "login"
