"""AI yordamchi jurnali (CLAUDE.md 13, 6-band): har bir savol, SQL va natija hajmi. Natija qatorlarining o'zi saqlanmaydi."""

from django.db import models


class AIQuery(models.Model):
    class Kind(models.TextChoices):
        ASK = "ask", "Savol"
        ANALYZE = "analyze", "Tahlil"

    class Status(models.TextChoices):
        OK = "ok", "Bajarildi"
        NO_SQL = "no_sql", "SQL yozilmadi"
        BLOCKED = "blocked", "Tekshiruvdan o'tmadi"
        ERROR = "error", "Xato"

    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.ASK)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="+")
    question = models.TextField("Savol")
    sql = models.TextField("SQL", blank=True)
    title = models.CharField(max_length=200, blank=True)
    chart = models.JSONField(default=dict, blank=True)
    note = models.TextField("AI izohi", blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.OK, db_index=True)
    error = models.CharField(max_length=400, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    truncated = models.BooleanField(default=False)
    uses_pii = models.BooleanField("Shaxsiy ma'lumot ustunlari", default=False)
    llm_calls = models.PositiveSmallIntegerField(default=0)
    provider = models.CharField(max_length=20, blank=True)
    model = models.CharField(max_length=60, blank=True)
    llm_ms = models.PositiveIntegerField(default=0)
    db_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "AI so'rovi"
        verbose_name_plural = "AI so'rovlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.question[:60]}"
