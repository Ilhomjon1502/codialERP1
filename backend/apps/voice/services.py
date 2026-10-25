"""Telegram ovozli buyruqlar (faqat Bosh menejer, buyurtmachi qarori 2026-10-25).

Oqim: ovoz yoki matn → Gemini (matn + bandlar) → savollarga darhol javob (AI yordamchi), amal va topshiriqlar uchun
yozma tasdiq kartasi → «✅ Tasdiqlash» bosilsa mavjud servislar bajaradi (ruxsat, qoldiq, limit, audit — saytdagidek).
Tugmalar: `vc:ok|no|ed:<id>`, tanlash `vc:pk:<id>:<band>:<variant>`. «✏️ Tuzatish» yoki kartaga javob (reply) — tuzatish."""

import datetime
import html
import json
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.models import User
from apps.ai_assistant import providers
from apps.ai_assistant import services as ai
from apps.ai_assistant.models import AIQuery
from apps.core import audit
from apps.core.permissions import role_code
from apps.core.roles import RoleCode
from apps.notifications import services as bot
from apps.notifications.models import TelegramLink

from . import actions, parser
from .models import VoiceCommand


def escape(s):
    """Telegram HTML uchun (apostrof o'zgarmaydi: «g'azna»)."""
    return html.escape(str(s), quote=False)

log = logging.getLogger(__name__)
St = VoiceCommand.Status

ALLOWED_ROLES = {RoleCode.BOSH_MENEJER}
TTL = datetime.timedelta(minutes=30)  # tasdiqlanmagan karta shuncha vaqtdan keyin eskiradi
DAILY_LIMIT = 150
MAX_SECONDS = 600
MAX_ROWS = 20
TEXT_LIMIT = 3900
HELP = ("Tushunmadim. Men qila oladiganlar:\n"
        "• istalgan savol (pul, g'azna, qarzdorlar, lidlar, davomat, oyliklar…)\n"
        "• xarajat, to'lov, kreditor amali, oylik berish, ichki o'tkazma, pul ayirboshlash — yangi kiritish, o'zgartirish, o'chirish\n"
        "• o'tkazma, naqdsiz to'lov va chegirmani tasdiqlash\n"
        "• oylikka bonus, jarima, belgilangan oylik\n"
        "• xodimga topshiriq berish, uni yopish, bekor qilish, muddatini o'zgartirish\n"
        "• lid: yangi, holat, qayta bog'lanish vaqti, guruh, izoh, o'chirish\n"
        "• shartnoma: tuzish, to'xtatish, boshqa guruhga o'tkazish, qayta faollashtirish\n"
        "• davomat olish va kelmaganlar bilan bog'lanish natijasi\n"
        "Qaytadan, aniqroq ayting.")


# ------------------------------------------------------------------ Telegram

def send(chat, text, markup=None):
    extra = {"reply_markup": json.dumps(markup)} if markup is not None else {}
    return bot.api("sendMessage", chat_id=chat, text=text[:TEXT_LIMIT], parse_mode="HTML", disable_web_page_preview="true", **extra)


def edit(chat, message_id, text, markup=None):
    try:
        bot.api("editMessageText", chat_id=chat, message_id=message_id, text=text[:TEXT_LIMIT], parse_mode="HTML",
                disable_web_page_preview="true", reply_markup=json.dumps(markup or {"inline_keyboard": []}))
    except RuntimeError as e:
        if "not modified" not in str(e):
            raise


def user_for_chat(chat_id):
    link = TelegramLink.objects.filter(chat_id=chat_id, user__employment_status=User.Employment.ACTIVE).select_related("user__role").first()
    return link.user if link else None


def allowed(user):
    return user is not None and role_code(user) in ALLOWED_ROLES


# ------------------------------------------------------------------ kirish nuqtasi (run_bot)

def handle_update(msg):
    """Shaxsiy chatdagi xabar. True — ovozli buyruq sifatida qabul qilindi (run_bot boshqa ishlov bermaydi)."""
    chat = (msg.get("chat") or {}).get("id")
    voice = msg.get("voice") or msg.get("audio")
    text = (msg.get("text") or "").strip()
    if not chat or (not voice and not text) or text.startswith("/"):
        return False
    user = user_for_chat(chat)
    if not allowed(user):
        if voice and user is not None:
            send(chat, "Ovozli buyruqlar faqat Bosh menejer uchun.")
            return True
        return False
    try:
        process(user, chat, msg)
    except Exception:  # noqa: BLE001 — bot to'xtamasin
        log.exception("Ovozli buyruqda xato")
        send(chat, "⚠️ Kutilmagan xato. Qayta urinib ko'ring yoki saytda kiriting.")
    return True


def _said_at(msg):
    ts = (msg.get("forward_origin") or {}).get("date") or msg.get("forward_date") or msg.get("date")
    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC) if ts else timezone.now()


def _editing(user, chat, msg):
    """Tuzatilayotgan buyruq: kartaga javob (reply) yoki «✏️ Tuzatish» bosilgan oxirgi buyruq."""
    reply = (msg.get("reply_to_message") or {}).get("message_id")
    qs = VoiceCommand.objects.filter(user=user, chat_id=chat, created_at__gte=timezone.now() - TTL)
    if reply:
        cmd = qs.filter(message_id=reply, status__in=[St.DRAFT, St.EDITING]).first()
        if cmd:
            return cmd
    return qs.filter(status=St.EDITING).order_by("-created_at").first()


def process(user, chat, msg):
    voice = msg.get("voice") or msg.get("audio")
    text = (msg.get("text") or "").strip()
    today = timezone.localdate()
    if VoiceCommand.objects.filter(user=user, created_at__date=today).count() >= DAILY_LIMIT:
        send(chat, f"Bugungi limit tugadi ({DAILY_LIMIT} ta buyruq). Ertaga yana foydalanish mumkin.")
        return None
    if voice and int(voice.get("duration") or 0) > MAX_SECONDS:
        send(chat, f"Ovozli xabar juda uzun ({MAX_SECONDS // 60} daqiqagacha). Bo'lib yuboring.")
        return None
    parent = _editing(user, chat, msg)
    placeholder = send(chat, "🎧 Eshityapman…" if voice else "⏳ Tahlil qilyapman…")["message_id"]
    said_at = _said_at(msg) if parent is None else parent.said_at
    cmd = VoiceCommand(user=user, chat_id=chat, is_voice=bool(voice), duration=int((voice or {}).get("duration") or 0), said_at=said_at,
                       parent=parent, message_id=placeholder, created_by=user, updated_by=user)
    try:
        audio = (bot.download_file(voice["file_id"]), voice.get("mime_type") or "audio/ogg") if voice else None
        out, cmd.model, cmd.llm_ms = parser.parse(user, text=text, audio=audio, said_at=said_at, previous=parent)
    except (providers.ProviderError, RuntimeError, OSError) as e:
        cmd.status, cmd.error = St.FAILED, str(e)[:500]
        cmd.save()
        edit(chat, placeholder, f"⚠️ {escape(str(e))}")
        return cmd
    cmd.transcript = out["transcript"] if voice else text  # yozma xabar — o'zi (Gemini qayta yozmasin)
    questions = [i for i in out["items"] if i["type"] == "question" and str(i.get("text") or "").strip()]
    cmd.items = [{"type": i["type"], "raw": {k: v for k, v in i.items() if k != "type"}, "picked": {}, "result": None}
                 for i in out["items"] if i["type"] != "question"]
    cmd.status = St.DRAFT if cmd.items else St.ANSWERED
    cmd.save()
    if parent is not None:
        parent.status = St.REPLACED
        parent.save(update_fields=["status", "updated_at"])
        if parent.message_id:
            edit(chat, parent.message_id, render(parent, footer="✏️ <i>Tuzatildi — yangi karta pastda</i>")[0])
    if cmd.items:
        body, markup = render(cmd)
        edit(chat, placeholder, body, markup)
        cmd.save(update_fields=["items"])
    else:
        head = f"🎙 «{escape(cmd.transcript)}»" if cmd.is_voice and cmd.transcript else ""
        if not questions:
            edit(chat, placeholder, "\n\n".join(x for x in (head, escape(out["reply"]) if out["reply"] else HELP) if x))
        else:
            edit(chat, placeholder, head or "⏳")
    for q in questions:
        send(chat, answer(user, str(q["text"]).strip()))
    return cmd


# ------------------------------------------------------------------ tasdiq kartasi

def said_text(cmd):
    """Menejer aytgan matn (tuzatishda — oldingi xabarlar bilan birga)."""
    parts, c = [], cmd
    while c is not None and len(parts) < 5:
        parts.append(c.transcript or "")
        c = c.parent
    since = cmd.created_at - datetime.timedelta(hours=2) if cmd.created_at else timezone.now() - datetime.timedelta(hours=2)
    recent = VoiceCommand.objects.filter(user=cmd.user, status=St.DONE, created_at__gte=since).exclude(pk=cmd.pk).order_by("-created_at")[:3]
    parts += [r.transcript for r in recent]  # «yana 50 ming bonus» — xodim oldingi buyruqda aytilgan (Gemini'ga ham shu kontekst boradi)
    return " ".join(parts)


def render(cmd, footer=""):
    """Karta matni va tugmalari. Tanlash kerak bo'lgan birinchi band uchun variant tugmalari; `item["need"]` ga variant id'lari yoziladi."""
    ctx = actions.Ctx(cmd.user, cmd.said_at, said_text(cmd))
    parts = [f"🎙 «{escape(cmd.transcript)}»"] if cmd.transcript else []
    ready, rows, need_shown = 0, [], False
    for n, item in enumerate(cmd.items, 1):
        item.pop("need", None)
        if item["type"] not in actions.HANDLERS:
            parts.append(f"{n}) ❓ Tushunilmadi: {escape(str(item['raw'].get('text') or item['type']))}")
            continue
        if item.get("result"):
            parts.append(f"{n}) {item['result']}")
            continue
        r, need, err = actions.resolve(ctx, item)
        if r is not None:
            ready += 1
            parts.append(f"{n}) <b>{r.title}</b>\n" + "\n".join(f"   {line}" for line in r.lines))
        elif need is not None:
            parts.append(f"{n}) ❔ {escape(need.label)}")
            if not need_shown:
                need_shown = True
                item["need"] = {"field": need.field, "ids": [o[0] for o in need.options]}
                rows += [[{"text": f"{n}) {label}"[:60], "callback_data": f"vc:pk:{cmd.pk}:{n - 1}:{j}"}] for j, (_, label) in enumerate(need.options)]
        else:
            parts.append(f"{n}) ⚠️ {escape(err or '')} — bajarilmaydi")
    if footer:
        parts.append(footer)
        return "\n\n".join(parts), None
    if cmd.status != St.DRAFT:
        return "\n\n".join(parts), None
    bottom = []
    if ready and not need_shown:
        bottom.append({"text": f"✅ Tasdiqlash ({ready})" if len(cmd.items) > 1 else "✅ Tasdiqlash", "callback_data": f"vc:ok:{cmd.pk}"})
    bottom += [{"text": "✏️ Tuzatish", "callback_data": f"vc:ed:{cmd.pk}"}, {"text": "❌ Bekor", "callback_data": f"vc:no:{cmd.pk}"}]
    if not ready and not need_shown and all(i["type"] not in actions.HANDLERS for i in cmd.items):
        parts.append(HELP)
    parts.append("Tanlang:" if need_shown else ("Tasdiqlaysizmi?" if ready else "Bajariladigan amal yo'q — tuzating yoki bekor qiling."))
    return "\n\n".join(parts), {"inline_keyboard": [*rows, bottom]}


def on_callback(cb):
    """`vc:` tugmalari. Javob — callback ostida qisqa matn; karta o'zi yangilanadi."""
    chat = (cb.get("from") or {}).get("id")
    try:
        _, op, pk, *rest = (cb.get("data") or "").split(":")
    except ValueError:
        return _answer(cb, "Noma'lum amal")
    user = user_for_chat(chat)
    if not allowed(user):
        return _answer(cb, "Ruxsat yo'q")
    with transaction.atomic():
        cmd = VoiceCommand.objects.select_for_update().filter(pk=pk, user=user).first()
        if cmd is None:
            return _answer(cb, "Buyruq topilmadi")
        if cmd.status not in (St.DRAFT, St.EDITING):
            return _answer(cb, f"Bu buyruq allaqachon: {cmd.get_status_display().lower()}")
        if timezone.now() - cmd.created_at > TTL and op != "no":
            cmd.status = St.CANCELLED
            cmd.save(update_fields=["status", "updated_at"])
            edit(cmd.chat_id, cmd.message_id, render(cmd, footer="⌛ <i>Muddati o'tdi — qaytadan yuboring</i>")[0])
            return _answer(cb, "Muddati o'tdi (30 daqiqa)")
        if op == "no":
            cmd.status = St.CANCELLED
            cmd.save(update_fields=["status", "updated_at"])
            edit(cmd.chat_id, cmd.message_id, render(cmd, footer="❌ <i>Bekor qilindi</i>")[0])
            return _answer(cb, "Bekor qilindi")
        if op == "ed":
            cmd.status = St.EDITING
            cmd.save(update_fields=["status", "updated_at"])
            edit(cmd.chat_id, cmd.message_id, render(cmd, footer="✏️ <i>Nimani o'zgartirish kerak? Ovoz yoki yozma yuboring.</i>")[0])
            return _answer(cb, "Tuzatishni yuboring")
        if op == "pk":
            return _pick(cb, cmd, rest)
        if op == "ok" and cmd.status == St.DRAFT:
            return _confirm(cb, cmd)
    return _answer(cb, "Noma'lum amal")


def _pick(cb, cmd, rest):
    try:
        i, j = int(rest[0]), int(rest[1])
        item = cmd.items[i]
        field, value = item["need"]["field"], item["need"]["ids"][j]
    except (IndexError, KeyError, TypeError, ValueError):
        return _answer(cb, "Variant eskirgan — kartani qayta yuboring")
    item.setdefault("picked", {})[field] = value
    body, markup = render(cmd)
    cmd.save(update_fields=["items", "updated_at"])
    edit(cmd.chat_id, cmd.message_id, body, markup)
    return _answer(cb, "Tanlandi")


def _confirm(cb, cmd):
    ctx = actions.Ctx(cmd.user, cmd.said_at, said_text(cmd))
    tag = f"🎙 Telegram ovozli buyruq: «{cmd.transcript[:200]}»" if cmd.is_voice else f"✈️ Telegram buyruq: «{cmd.transcript[:200]}»"
    done = 0
    with audit.tagged(tag):
        for item in cmd.items:
            if item["type"] not in actions.HANDLERS or item.get("result"):
                continue
            item["result"] = actions.execute(ctx, item)
            done += item["result"].startswith("✅")
    cmd.status = St.DONE
    cmd.save(update_fields=["items", "status", "updated_at"])
    edit(cmd.chat_id, cmd.message_id, render(cmd, footer=f"<i>Tasdiqlandi {timezone.localtime():%H:%M}</i>")[0])
    return _answer(cb, f"✅ Bajarildi: {done} ta" if done else "⚠️ Bajarilmadi — sababi kartada")


def _answer(cb, text):
    try:
        bot.api("answerCallbackQuery", callback_query_id=cb["id"], text=text[:190])
    except Exception:  # noqa: BLE001
        log.exception("Callback javobi yuborilmadi")
    return text


# ------------------------------------------------------------------ savollar (AI yordamchi orqali)

def _cell(v):
    if isinstance(v, bool) or v is None:
        return "" if v is None else ("ha" if v else "yo'q")
    if isinstance(v, (int, float)):
        return f"{v:,.0f}".replace(",", " ") if abs(v) >= 1000 or float(v).is_integer() else f"{v:.1f}"
    return str(v)


def answer(user, question):
    """AI yordamchi (saytdagi bilan bir xil: Gemini → SQL → server tekshiruvi). Natija Gemini'ga yuborilmaydi."""
    head = f"❓ <b>{escape(question)}</b>"
    try:
        r = ai.ask(user, question)
    except (ValidationError, APIException) as e:
        return f"{head}\n⚠️ {escape(actions.error_text(e))}"
    if r["status"] != AIQuery.Status.OK:
        return f"{head}\n⚠️ {escape(r['error'] or r['note'] or 'Javob topilmadi')}"
    out = [head]
    if r["title"]:
        out.append(f"📊 {escape(r['title'])}")
    cols, rows = r["columns"], r["rows"]
    if not rows:
        out.append("Natija bo'sh.")
        out += [escape(x) for x in r["explain"]]
    elif len(rows) == 1 and len(cols) <= 4:
        out += [f"{escape(str(c))}: <b>{escape(_cell(v))}</b>" for c, v in zip(cols, rows[0], strict=False)]
    else:
        table = [" | ".join(str(c) for c in cols)] + [" | ".join(_cell(v) for v in row) for row in rows[:MAX_ROWS]]
        out.append("<pre>" + escape("\n".join(table))[:3000] + "</pre>")
        if len(rows) > MAX_ROWS or r["truncated"]:
            out.append(f"… jami {r['row_count']} qator. To'liq ro'yxat: sayt → AI yordamchi.")
    if r["note"]:
        out.append(f"<i>{escape(r['note'])}</i>")
    return "\n".join(out)
