from django.contrib import admin

from .models import AIQuery


@admin.register(AIQuery)
class AIQueryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "kind", "status", "question", "row_count", "llm_ms", "db_ms")
    list_filter = ("kind", "status")
    readonly_fields = [f.name for f in AIQuery._meta.fields]
