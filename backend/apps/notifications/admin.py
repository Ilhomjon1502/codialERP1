from django.contrib import admin

from .models import ExtraRecipient, Outbox, TelegramLink

admin.site.register(TelegramLink)
admin.site.register(Outbox)
admin.site.register(ExtraRecipient)
