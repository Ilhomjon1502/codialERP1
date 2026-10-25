from common import SAVE, f, lesson, option, outro


@lesson("09", "davomat", "Davomat")
async def l09(L):
    await L.card("9-dars", "Davomat", "Darsga kim keldi, kim kelmadi va ular bilan bogʻlanish",
                 ["Davomatni kim oladi", "Davomat olish va tuzatish", "Keldi, sababli, besabab",
                  "Kelmaganlar bilan bogʻlanish", "Davomat statistikasi", "Qoldirilgan darslar"],
                 text="To'qqizinchi darsda davomat bilan ishlashni o'rganamiz. Davomat — talaba qarzi va ustoz oyligi hisoblanadigan asosiy ma'lumot.")
    await L.uncard()
    await L.say("Davomatni odatda ustoz oladi — telefonidan yoki Telegram bot orqali. Sizning vazifangiz — tekshirish, kerak bo'lsa tuzatish va kelmaganlar bilan bog'lanish.")
    await L.nav("attendance", "Davomatlar")
    if await L.exists("#view .alert.info"):
        await L.say("Tepada — bugun davomati hali olinmagan guruhlar. Dars tugasa-yu davomat olinmagan bo'lsa, ustozga eslating yoki o'zingiz oling.",
                    L.show("#view .alert.info", "Olinmagan davomat", side="below"))
    await L.say("To'rtta tab: davomat olish, kelmaganlar, statistika va qoldirilgan darslar.",
                L.show("#view .tabs", "Tablar", side="below"))
    await L.say("Davomat olish uch qadam: avval sana, keyin kurs, keyin shu kungi guruh.",
                L.show("#view .take-head", "Uch qadam", side="below"))
    await L.say("Sana — bugun. O'tgan sanadagi xatoni tuzatish uchun boshqa sanani tanlashingiz mumkin.",
                L.show("#att-date", "Sana", side="below"))
    if await L.exists("#att-course"):
        val = await option(L, "#att-course", match="Kompyuter") or await option(L, "#att-course")
        await L.say("Kursni tanlaymiz. Ro'yxatda faqat shu kuni darsi bor kurslar chiqadi.",
                    L.choose("#att-course", val, label="Kurs"))
        await L.wait(1.0)
    if await L.exists("#att-group"):
        # O'quvchisi bor guruhni tanlaymiz (bo'sh guruhda tugmalar chiqmaydi)
        val = await option(L, "#att-group")
        await L.say("Endi guruhni tanlaymiz: dars vaqti va guruh nomi yozilgan.",
                    L.choose("#att-group", val, label="Guruh"))
        for n in range(1, 8):
            await L.wait(1.0)
            if L.dry or await L.exists(".att-list li .att-btns"):
                break
            val = await option(L, "#att-group", n)
            if not val:
                break
            await L.choose("#att-group", val, label="Guruh")
    await L.wait_for(".att-card")
    await L.say("Guruh talabalari chiqdi. Har bir talaba yonida to'rtta tugma: Keldi, Sababli, Besabab va chiziqcha — nofaol.",
                L.show(".att-list li:first-child .att-btns", "Tugmalar", side="below"))
    await L.say("Qizil ism — qarzdor talaba, ostida qarz summasi.")
    await L.say("Birinchi talaba keldi — «Keldi»ni bosamiz.",
                L.click(".att-list li:not(.done) .abtn.g", "Keldi", side="left"))
    await L.wait(1.0)
    await L.say("Yana bir talaba kasal bo'lgan va oldindan aytgan — «Sababli». Sababini yozish majburiy.",
                L.click(".att-list li:not(.done) .abtn.y", "Sababli", side="left"))
    await L.wait_for(f("comment", "textarea"))
    await L.say("Sababini yozamiz.", L.type(f("comment", "textarea"), "Kasal, onasi qo'ng'iroq qildi", "Sabab", delay=40))
    await L.say("«Belgilash»ni bosamiz.", L.click(SAVE, "Belgilash", side="above"))
    await L.wait(1.0)
    await L.say("Bir talaba sababsiz kelmadi — «Besabab».",
                L.click(".att-list li:not(.done) .abtn.r", "Besabab", side="left"))
    await L.wait(1.0)
    if await L.exists('[data-act="att-all"]'):
        await L.say("Qolganlarning hammasi kelgan bo'lsa, «Hammasi keldi» tugmasi bilan bir bosishda belgilaymiz.",
                    L.click('[data-act="att-all"]', "Hammasi keldi", side="left"))
        await L.wait(1.2)
    await L.say("Hamma belgilandi. Yashil chiziq — davomat to'liq olingani.",
                L.show(".att-card h2", "Belgilandi", side="below"))
    await L.say("Muhim: dars bo'lgan bo'lsa, talaba kelmasa ham dars narxi qarzga yoziladi. Faqat «nofaol» belgisida qarz yozilmaydi.")
    if await L.exists("#att-sub"):
        await L.say("Agar darsni boshqa ustoz o'tgan bo'lsa, «o'rindosh» belgisini qo'yib, o'sha ustozni tanlaysiz. Ustoz oyligi darsni o'tgan odamga yoziladi.",
                    L.show("label:has(#att-sub)", "Oʻrindosh", side="below"))
    await L.clear()
    await L.say("Endi «Kelmaganlar» tabi. Bu yerda shu oyda kelmagan talabalar ro'yxati.",
                L.click('#view .tabs a[href*="tab=absent"]', "Kelmaganlar", side="below", wait=1.5))
    await L.say("Har bir qatorda: sana, talaba va telefoni, guruh, status va bog'lanish holati.",
                L.show("#view .tbl thead", "Ustunlar", side="below"))
    await L.say("Kelmagan talaba yoki ota-onasiga qo'ng'iroq qilib, natijasini «Bog'lanish holati»ga yozasiz.",
                L.show('#view select[data-act-change="att-contact"]', "Bogʻlanish holati", side="left"))
    await L.say("Masalan, telefon ko'tarilmadi — «Tushib bo'lmadi».",
                L.choose('#view select[data-act-change="att-contact"]', "Tushib bo'lmadi", label="Tushib boʻlmadi"))
    await L.wait(1.2)
    await L.say("Gaplashgan bo'lsangiz — «Gaplashildi». Bunda izoh majburiy: nima deyildi.",
                L.choose('#view tbody tr:nth-child(2) select[data-act-change="att-contact"]', "Gaplashildi", label="Gaplashildi"))
    await L.wait_for(f("comment", "textarea"))
    await L.type(f("comment", "textarea"), "Ertaga darsga keladi, betob edi", "Nima deyildi", delay=40)
    await L.say("Saqlaymiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("Qo'ng'iroqlar bo'limida ham kelmagan talaba bilan gaplashilgan bo'lsa, shu belgini bir tugma bilan qo'yish mumkin.")
    await L.clear()
    await L.say("«Statistika» tabi — oy bo'yicha barcha davomat qatorlari.",
                L.click('#view .tabs a[href*="tab=stats"]', "Statistika", side="below", wait=1.8))
    await L.say("Chapda — sanalar va har kuni nechta qator. Sanani bossangiz, faqat shu kun qoladi.",
                L.show("#view .tree", "Sanalar", side="right"))
    await L.say("Tepada filtrlar: oy, kurs, guruh va talaba ismi.",
                L.show("#view .filters", "Filtrlar", side="below"))
    await L.say("Jadvalda statusni shu yerning o'zida o'zgartirish mumkin — qarz darhol qayta hisoblanadi.",
                L.show("#view .att-inline", "Statusni tuzatish", side="right"))
    val = await option(L, 'select[data-filter="ast:group"]')
    await L.say("Guruhni tanlasangiz, davomat olinmagan sanalar qizil bilan ko'rsatiladi — ularni to'ldirish kerak.",
                L.choose('select[data-filter="ast:group"]', val, label="Guruh"))
    await L.wait(1.5)
    await L.say("«Jamlama» tugmasi — guruh va ustozlar bo'yicha davomat foizi.",
                L.click('[data-act="ast-view"][data-id="sum"]', "Jamlama", side="below", wait=1.5))
    await L.say("Davomat foizi sakson foizdan past bo'lsa, qizil bilan chiqadi.",
                L.show("#view .grid-2 .card:first-child", "Guruhlar boʻyicha", side="right"))
    await L.click('[data-act="ast-view"][data-id="rows"]', wait=1.0)
    await L.clear()
    await L.say("Oxirgi tab — «Qoldirilgan darslar». Talaba besabab kelmagan darsni ustoz keyin alohida o'tib bersa, «Darsni yetkazdim» so'rovini yuboradi.",
                L.click('#view .tabs a[href*="tab=makeup"]', "Qoldirilgan darslar", side="below", wait=1.5))
    await L.say("So'rov tasdiqlansa, «Besabab» «Sababli»ga o'zgaradi va ustozga haqi yoziladi. So'rovlar bu yerda va «Tasdiqlashlar» bo'limida chiqadi.")
    await L.clear()
    await outro(L, "Guruhlar va dars jadvali")
