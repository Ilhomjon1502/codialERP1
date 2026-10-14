"""AppSheet (Google Sheets .xlsx) dan faol shartnomalarni ko'chirish (M10, docs/decisions.md 2026-10-14).

    python manage.py import_appsheet --file ../import_data/Codial1.1.xlsx              # sinov rejimi (standart): bazaga yozilmaydi
    python manage.py import_appsheet --file ... --on 2026-11-01 --commit              # haqiqiy import

Qayta ishga tushirish dublikat yaratmaydi (legacy_id). Xodimlarga xat yuborilmaydi.
Diqqat: guruh, talaba va shartnoma maydonlari Excel'dagidek qayta yoziladi — o'tish kunidan keyin (yangi tizimda ish boshlangach)
qayta ishga tushirmang. Tizimda bor xodimlar (pochta bo'yicha) faqat bog'lanadi, roli va ismi o'zgarmaydi.
"""

import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.importer import services


class Command(BaseCommand):
    help = "AppSheet .xlsx eksportidan faol shartnomalar va ularga kerakli ma'lumotlarni ko'chiradi"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Google Sheets'dan yuklab olingan .xlsx")
        parser.add_argument("--on", help="Qaysi sanada faol shartnomalar (YYYY-MM-DD), standart — bugun")
        parser.add_argument("--commit", action="store_true", help="Haqiqatan yozish (busiz — sinov rejimi)")

    def handle(self, *args, **opts):
        on = None
        if opts["on"]:
            try:
                on = datetime.date.fromisoformat(opts["on"])
            except ValueError:
                raise CommandError("--on: YYYY-MM-DD ko'rinishida") from None
        try:
            rep = services.run(opts["file"], on=on, dry_run=not opts["commit"])
        except (FileNotFoundError, ValueError) as e:
            raise CommandError(str(e)) from None
        self.stdout.write("\n".join(rep.lines()))
        if rep.errors:
            self.stdout.write(self.style.WARNING(f"\n{len(rep.errors)} ta yozuv ko'chirilmadi — sababi yuqorida"))
