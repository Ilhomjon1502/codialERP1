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
                params = {"timeout": 20, "allowed_updates": '["message"]'}
                if offset:
                    params["offset"] = offset
                for upd in services.api("getUpdates", **params):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message") or {}
                    chat = (msg.get("chat") or {}).get("id")
                    if chat and msg.get("chat", {}).get("type") == "private":
                        reply = services.handle_message(chat, msg.get("text", ""), (msg.get("from") or {}).get("username", ""))
                        services.api("sendMessage", chat_id=chat, text=reply)
                if time.monotonic() - last_tick >= 60:  # har daqiqada: boshlangan darslar → ustozga eslatma (1–2 yengil so'rov)
                    last_tick = time.monotonic()
                    close_old_connections()
                    reminders.lesson_starts()
                services.send_pending()
            except Exception:  # noqa: BLE001 — tarmoq xatosi botni to'xtatmasin
                log.exception("Bot siklida xato")
                time.sleep(10)
