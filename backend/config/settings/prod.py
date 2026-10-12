"""Server (test va asosiy muhit): PostgreSQL, HTTPS, xavfsiz cookie'lar. Barcha sirlar .env da."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import SECRET_KEY, env_bool

if not SECRET_KEY or len(SECRET_KEY) < 40:
    raise ImproperlyConfigured("SECRET_KEY .env da berilmagan yoki juda qisqa (kamida 40 belgi)")

DEBUG = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# HSTS subdomenlar va preload uchun ataylab yoqilmagan: codial.uz ning boshqa subdomenlari HTTPS'siz bo'lishi mumkin
SILENCED_SYSTEM_CHECKS = [*SILENCED_SYSTEM_CHECKS, "security.W005", "security.W021"]  # noqa: F405
