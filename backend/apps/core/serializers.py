from rest_framework import serializers

from apps.core.models import AuditLog


def _fmt(v):
    if v in (None, "", []):
        return "∅"
    if isinstance(v, list):
        return "[" + ", ".join(map(str, v)) + "]"
    return str(v)


class AuditLogSerializer(serializers.ModelSerializer):
    obj = serializers.CharField(source="object_repr")
    detail = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ["id", "at", "user", "action", "model", "object_id", "obj", "changes", "detail"]

    def get_detail(self, a):
        parts = [f"{f}: {_fmt(old)} → {_fmt(new)}" for f, old, new in (a.changes or [])]
        if a.detail:
            parts.insert(0, a.detail)
        return "; ".join(parts)
