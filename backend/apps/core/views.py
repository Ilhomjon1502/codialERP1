from django.db import connection
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([])
def health(request):
    """Monitoring (deploy/healthcheck.sh): sayt va baza javob beryaptimi. Ma'lumot qaytarmaydi."""
    with connection.cursor() as cur:
        cur.execute("SELECT 1")
    return Response({"ok": True})
