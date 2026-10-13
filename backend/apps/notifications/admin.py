from django.contrib import admin

from .models import Outbox, TelegramLink

admin.site.register(TelegramLink)
admin.site.register(Outbox)
