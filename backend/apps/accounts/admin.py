from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Role, RolePermission, User


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "sort"]
    inlines = [RolePermissionInline]
    filter_horizontal = ["can_assign"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["full_name"]
    list_display = ["full_name", "email", "role", "employment_status", "is_staff"]
    list_filter = ["role", "employment_status", "is_staff"]
    search_fields = ["full_name", "email", "phone"]
    filter_horizontal = ["branches", "groups", "user_permissions"]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Xodim", {"fields": ["full_name", "phone", "role", "branches", "teams", "employment_status"]}),
        ("Texnik", {"fields": ["is_staff", "is_superuser", "last_login", "legacy_id"]}),
    ]
    add_fieldsets = [(None, {"classes": ["wide"], "fields": ["email", "full_name", "role", "password1", "password2"]})]
    readonly_fields = ["last_login"]
