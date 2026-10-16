from django.contrib import admin

from .models import StaffTask


@admin.register(StaffTask)
class StaffTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "assignee", "created_by", "due_at", "status")
    list_filter = ("status",)
