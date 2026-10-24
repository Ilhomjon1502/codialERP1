"""Mijozlar boti jarayoni (Docker'da `clientbot` xizmati): o'quvchi va vasiylar xabarlarini o'qiydi va navbatdagi xabarlarni yuboradi.

    python manage.py run_clientbot
"""

import json
import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.clientbot import services

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Mijozlar Telegram boti: long polling + xabarlar navbatini yuborish"

    def handle(self, *args, **opts):
        if not settings.CLIENT_BOT_TOKEN:
            self.stdout.write("CLIENT_BOT_TOKEN berilmagan — bot kutish rejimida (deploy/set-clientbot.sh bilan sozlang)")
            while not settings.CLIENT_BOT_TOKEN:
                time.sleep(300)
        me = services.api("getMe")
        self.stdout.write(self.style.SUCCESS(f"Mijozlar boti ishga tushdi: @{me.get('username')}"))
        try:  # Telegram'dagi «/» menyusi
            commands = [{"command": "menu", "description": "To'lov, davomat va dars jadvali"}, {"command": "stop", "description": "Bog'lanishni uzish"}]
            services.api("setMyCommands", commands=json.dumps(commands))
        except Exception:  # noqa: BLE001
            log.exception("Bot buyruqlari o'rnatilmadi")
        offset = None
        while True:
            try:
                params = {"timeout": 5, "allowed_updates": '["message", "callback_query"]'}
                if offset:
                    params["offset"] = offset
                for upd in services.api("getUpdates", **params):
                    offset = upd["update_id"] + 1
                    close_old_connections()
                    try:
                        if upd.get("callback_query"):
                            self.on_callback(upd["callback_query"])
                        else:
                            self.on_message(upd.get("message") or {})
                    except Exception:  # noqa: BLE001 — bitta xabar botni to'xtatmasin
                        log.exception("Mijozlar boti: xabar qayta ishlanmadi")
                close_old_connections()
                services.send_pending()
            except Exception:  # noqa: BLE001 — tarmoq xatosi botni to'xtatmasin
                log.exception("Mijozlar boti siklida xato")
                time.sleep(10)

    @staticmethod
    def send(chat, replies):
        for r in replies:
            extra = {"reply_markup": json.dumps(r.markup)} if r.markup else {}
            services.api("sendMessage", chat_id=chat, text=r.text, parse_mode="HTML", disable_web_page_preview="true", **extra)

    def on_message(self, msg):
        chat = msg.get("chat") or {}
        if chat.get("type") != "private" or not chat.get("id"):
            return
        frm = msg.get("from") or {}
        self.send(chat["id"], services.handle_message(chat["id"], msg.get("text", ""), frm.get("username", ""), frm.get("first_name", "")))

    def on_callback(self, cb):
        chat, message = (cb.get("from") or {}).get("id"), cb.get("message") or {}
        answer, replies = services.handle_callback(chat, cb.get("data") or "") if chat else ("Xatolik", [])
        try:
            services.api("answerCallbackQuery", callback_query_id=cb["id"], text=answer[:190])
            done = next((r for r in replies if r.done), None)
            if message.get("message_id") and (done or answer.startswith("Bu savol")):
                if done:  # tanlangan javob xabarda qoladi, tugmalar olib tashlanadi
                    services.api("editMessageText", chat_id=chat, message_id=message["message_id"], text=done.text, parse_mode="HTML")
                else:
                    services.api("editMessageReplyMarkup", chat_id=chat, message_id=message["message_id"], reply_markup=json.dumps({"inline_keyboard": []}))
            self.send(chat, [r for r in replies if not r.done])
        except Exception:  # noqa: BLE001
            log.exception("Mijozlar boti: callback javobi yuborilmadi")
