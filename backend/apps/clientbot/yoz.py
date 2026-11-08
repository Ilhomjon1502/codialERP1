"""«Codial Yoz» (yoz.codialinfo.uz) klaviatura trenajorini darslik ilovasiga ulash (2026-11-08).

- O'quvchi darslik ilovasida «⌨️ Klaviatura trenajori» ni bosadi → ilova qisqa **ulash kodi** beradi (15 daqiqa, bir marta)
  va Yoz'ni `?code=` bilan ochadi (Telegram Desktop/telefonda — o'sha oynada; boshqa kompyuterda — kodni o'zi kiritadi).
- Yoz kodni **token**ga almashtiradi (120 kun) va saqlaydi; keyin har mashq natijasini `X-Yoz-Token` bilan yuboradi (`TypingSession`).
- Server hisoblaydi: jami vaqt, bugungi daqiqalar, seriya kunlari, eng yaxshi tezlik, aniqlik, boshlang'ich va hozirgi tezlik (o'sish).
- Natijalarni Yoz o'zi yuboradi, shuning uchun ular «o'quvchi aytgani»: me'yoriy chegaralar bilan tekshiriladi, xolos.
"""

import datetime

from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Max, Sum
from django.utils import timezone

from .models import TypingSession, YozPairing

SALT = "codial-yoz"
TOKEN_MAX_AGE = 120 * 24 * 3600
CODE_TTL = datetime.timedelta(minutes=15)
CODE_LEN = 6
MAX_BATCH = 100
MAX_SESSION_MS = 60 * 60 * 1000
MAX_WPM = 250
GOOD_ACCURACY = 90  # eng yaxshi tezlik: aniqligi shundan past mashqlar hisobga olinmaydi (Yoz o'tish sharti bilan bir xil)
ORIGINS = ("https://yoz.codialinfo.uz", "http://localhost:5520")  # CORS: faqat Yoz sayti


def make_token(student, account):
    return signing.dumps({"s": str(student.pk), "a": account.pk}, salt=SALT)


def read_token(token):
    """Token → (Student, BotAccount) yoki None (imzo noto'g'ri, eskirgan, o'quvchi o'chirilgan yoki akkaunt endi ulanmagan)."""
    from apps.crm.models import Student

    from .models import BotAccount, BotInvite

    try:
        data = signing.loads(token or "", salt=SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None
    st = Student.objects.filter(pk=data.get("s"), is_deleted=False).first()
    acc = BotAccount.objects.filter(pk=data.get("a")).first()
    if not st or not acc or not acc.links.filter(student=st, role=BotInvite.Role.STUDENT, is_active=True).exists():
        return None
    return st, acc


def new_pairing(student, account, now=None):
    now = now or timezone.now()
    YozPairing.objects.filter(student=student, account=account, used_at__isnull=True).delete()  # eski kod bekor bo'ladi
    for _ in range(5):
        try:
            with transaction.atomic():
                from .models import new_code

                return YozPairing.objects.create(student=student, account=account, code=new_code()[:CODE_LEN], expires_at=now + CODE_TTL)
        except IntegrityError:  # kod to'qnashdi
            continue
    raise RuntimeError("Ulash kodi yaratilmadi")


def exchange(code, now=None):
    """Kod → (token, Student) yoki None. Bir marta ishlaydi."""
    now = now or timezone.now()
    code = "".join(ch for ch in str(code or "").upper() if ch.isalnum())
    if len(code) != CODE_LEN:
        return None
    with transaction.atomic():
        pr = YozPairing.objects.select_for_update().select_related("student", "account").filter(code=code, used_at__isnull=True, expires_at__gt=now).first()
        if pr is None or pr.student.is_deleted:
            return None
        pr.used_at = now
        pr.save(update_fields=["used_at"])
    return make_token(pr.student, pr.account), pr.student


def _when(ms, now):
    try:
        at = datetime.datetime.fromtimestamp(float(ms) / 1000, tz=datetime.UTC)
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return at if at <= now + datetime.timedelta(days=1) and at >= now - datetime.timedelta(days=400) else None


def record(student, sessions, now=None):
    """Yoz yuborgan mashqlar ro'yxatini saqlaydi (client_id bo'yicha takrorlanmaydi). Qaytaradi: yangi saqlanganlar soni."""
    now = now or timezone.now()
    rows = []
    for x in list(sessions or [])[:MAX_BATCH]:
        if not isinstance(x, dict):
            continue
        cid, at = str(x.get("id") or "")[:40], _when(x.get("at"), now)
        try:
            ms, wpm, acc, stars = int(x.get("ms")), int(round(float(x.get("wpm")))), int(round(float(x.get("acc")))), int(x.get("stars") or 0)
        except (TypeError, ValueError):
            continue
        if not cid or at is None or not 1000 <= ms <= MAX_SESSION_MS or not 0 <= wpm <= MAX_WPM or not 0 <= acc <= 100:
            continue
        rows.append(TypingSession(student=student, client_id=cid, lesson_key=str(x.get("l") or "")[:40], at=at, duration_ms=ms, wpm=wpm, accuracy=acc,
                                  stars=max(0, min(3, stars))))
    if not rows:
        return 0
    have = set(TypingSession.objects.filter(student=student, client_id__in=[r.client_id for r in rows]).values_list("client_id", flat=True))
    new = [r for r in rows if r.client_id not in have]
    TypingSession.objects.bulk_create(new, ignore_conflicts=True)
    return len(new)


def summary(student, today=None):
    """Ilova va ERP uchun: jami vaqt, bugun, seriya, eng yaxshi tezlik, aniqlik, boshlang'ich va hozirgi tezlik, oxirgi 7 kun."""
    today = today or timezone.localdate()
    qs = TypingSession.objects.filter(student=student)
    agg = qs.aggregate(ms=Sum("duration_ms"), last=Max("at"))
    first3 = list(qs.order_by("at").values_list("wpm", flat=True)[:3])
    recent = list(qs.order_by("-at").values_list("wpm", "accuracy")[:5])
    by_day = {}
    for at, ms in qs.filter(at__gte=timezone.now() - datetime.timedelta(days=400)).values_list("at", "duration_ms"):
        d = timezone.localtime(at).date()
        by_day[d] = by_day.get(d, 0) + ms
    streak, d = 0, today if today in by_day else today - datetime.timedelta(days=1)
    while d in by_day:
        streak += 1
        d -= datetime.timedelta(days=1)
    good = qs.filter(accuracy__gte=GOOD_ACCURACY).aggregate(best=Max("wpm"))["best"]
    last20 = list(qs.order_by("-at").values_list("accuracy", flat=True)[:20])
    return {
        "sessions": qs.count(), "total_min": round((agg["ms"] or 0) / 60000), "today_min": round(by_day.get(today, 0) / 60000),
        "streak": streak, "best_wpm": good or 0, "avg_acc": round(sum(last20) / len(last20)) if last20 else None,
        "first_wpm": max(first3) if first3 else None, "recent_wpm": round(sum(w for w, _ in recent) / len(recent)) if recent else None,
        "last_at": agg["last"].isoformat() if agg["last"] else None,
        "week": [{"date": (today - datetime.timedelta(days=i)).isoformat(), "min": round(by_day.get(today - datetime.timedelta(days=i), 0) / 60000)} for i in range(6, -1, -1)],
    }


def minutes_since(student, days=1, now=None):
    """Oxirgi `days` kunda mashq qilingan daqiqalar (uy vazifasini baholash uchun)."""
    now = now or timezone.now()
    ms = TypingSession.objects.filter(student=student, at__gte=now - datetime.timedelta(days=days)).aggregate(s=Sum("duration_ms"))["s"] or 0
    return round(ms / 60000)
