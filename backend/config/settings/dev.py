"""Lokal ishlab chiqish: SQLite, DEBUG, xatlar konsolga chiqadi, front-end Django orqali beriladi."""

from .base import *  # noqa: F403
from .base import env

DEBUG = True
SECRET_KEY = env("SECRET_KEY", "dev-only-not-secret")
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
