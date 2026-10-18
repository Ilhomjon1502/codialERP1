"""Telegram bot jarayoni (Docker'da `bot` xizmati): kelgan xabarlarni o'qiydi (akkaunt bog'lash) va navbatdagi xabarlarni yuboradi.

    python manage.py run_bot
"""

import json
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.notifications import reminders, services, webapp
from apps.tasks import services as tasks

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Telegram bot: long polling + xabarlar navbatini yuborish"

    def handle(self, *args, **opts):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stdout.write("TELEGRAM_BOT_TOKEN berilmagan — bot kutish rejimida (deploy/set-telegram.sh bilan sozlang)")
            while not settings.TELEGRAM_BOT_TOKEN:
                time.sleep(300)
        me = services.api("getMe")
        self.stdout.write(self.style.SUCCESS(f"Bot ishga tushdi: @{me.get('username')}"))
        if webapp.enabled():  # bot menyusidagi doimiy «Davomat» tugmasi — Mini App
            try:
                services.api("setChatMenuButton", menu_button=json.dumps({"type": "web_app", "text": "Davomat", "web_app": {"url": webapp.url("attendance")}}))
            except Exception:  # noqa: BLE001
                log.exception("Menyu tugmasi o'rnatilmadi")
        offset, last_tick = None, 0.0
        while True:
            try:
                params = {"timeout": 5, "allowed_updates": '["message", "callback_query"]'}
                if offset:
                    params["offset"] = offset
                for upd in services.api("getUpdates", **params):
                    offset = upd["update_id"] + 1
                    if upd.get("callback_query"):  # xabardagi tugma (masalan topshiriq «✅ Bajarildi»)
                        self.on_callback(upd["callback_query"])
                        continue
                    msg = upd.get("message") or {}
                    chat = (msg.get("chat") or {}).get("id")
                    if chat and msg.get("chat", {}).get("type") in ("group", "supergroup"):  # guruhga yuborish uchun chat_id ni bilish (jurnalga)
                        log.warning("GURUH chat_id=%s nomi=%s", chat, (msg.get("chat") or {}).get("title"))
                    if chat and msg.get("chat", {}).get("type") == "private":
                        reply = services.handle_message(chat, msg.get("text", ""), (msg.get("from") or {}).get("username", ""))
                        services.api("sendMessage", chat_id=chat, text=reply)
                if time.monotonic() - last_tick >= 60:  # har daqiqada: boshlangan darslar → ustozga eslatma (1–2 yengil so'rov)
                    last_tick = time.monotonic()
                    close_old_connections()
                    reminders.lesson_starts()
                    reminders.debt_before_lessons()
                    tasks.due_reminders()
                services.send_pending()
            except Exception:  # noqa: BLE001 — tarmoq xatosi botni to'xtatmasin
                log.exception("Bot siklida xato")
                time.sleep(10)

    def on_callback(self, cb):
        data, chat = cb.get("data") or "", (cb.get("from") or {}).get("id")
        text = "Noma'lum amal"
        if data.startswith("td:") and chat:
            close_old_connections()
            text = tasks.done_from_telegram(chat, data[3:])
        try:
            services.api("answerCallbackQuery", callback_query_id=cb["id"], text=text)
            msg = cb.get("message") or {}
            if text.startswith("✅") and msg.get("message_id"):  # tugma qayta bosilmasin
                services.api("editMessageReplyMarkup", chat_id=msg["chat"]["id"], message_id=msg["message_id"], reply_markup=json.dumps({"inline_keyboard": []}))
        except Exception:  # noqa: BLE001
            log.exception("Callback javobi yuborilmadi")

