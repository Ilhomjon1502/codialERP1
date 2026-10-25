from common import MODAL, SAVE, f, lesson, outro


@lesson("08", "qarzdorlar_sms", "Qarzdorlar, to'lovga tavsiya va SMS")
async def l08(L):
    await L.card("8-dars", "Qarzdorlar va SMS eslatma", "Kim qancha toʻlashi kerak va unga qanday eslatiladi",
                 ["«Toʻlovga tavsiya» roʻyxati", "Kurs va guruh boʻyicha daraxt", "Roʻyxatdan toʻlov qabul qilish",
                  "«✓ Toʻlov qilgan» belgisi", "SMS eslatma yuborish", "Haqiqiy qarz (davomat boʻyicha)"],
                 text="Sakkizinchi darsda qarzdorlar bo'limini va talabalarga SMS orqali to'lov eslatmasi yuborishni o'rganamiz.")
    await L.uncard()
    await L.nav("debtors", "Qarzdorlar")
    await L.say("Birinchi tab — «To'lovga tavsiya». Bu shu oy uchun hali to'lov qilmagan talabalar ro'yxati, ya'ni kimga eslatish kerakligi.",
                L.show("#view .tabs", "Ikki tab", side="below"))
    await L.say("Summa shu oyning kurs narxidan hisoblanadi: oldindan to'lagan puli va eski qarzi ham hisobga olinadi. Oy o'rtasida kelgan talabaga faqat qolgan darslar uchun.")
    await L.say("Chapda daraxt: «Barchasi», keyin kurslar va guruhlar. Har birida — tavsiya summasi.",
                L.show("#view .tree", "Daraxt", side="right"))
    await L.say("Kursni bossangiz, faqat shu kurs talabalari qoladi.",
                L.click("#view .tree a.tree-n:nth-child(2)", "Kurs", side="right", wait=1.2))
    await L.say("Yana «Barchasi»ni bosib, hamma ro'yxatga qaytamiz.",
                L.click("#view .tree a.tree-n:nth-child(1)", "Barchasi", side="right", wait=1.2))
    await L.say("Tepada ikki raqam: jami tavsiya summasi va muddati o'tganlar.",
                L.show("#view .settings-body .stats", "Jami", side="below"))
    await L.say("Jadvalda: talaba, telefonlari, guruhi, oylik narx, oldingi balans, shu oy to'lagani va to'lashi kerak bo'lgan summa.",
                L.show("#view .settings-body .tbl thead", "Ustunlar", side="below"))
    await L.say("«Holat» ustuni: to'lov muddati — har oyning o'ninchi sanasi. Undan keyin qizil «muddati o'tgan» yoziladi.",
                L.show("#view .settings-body .tbl tbody tr:first-child td[data-label='Holat']", "Muddat", side="left"))
    await L.clear()
    await L.say("Talaba to'lov olib kelsa, shu qatordagi «To'lov» tugmasini bosasiz — shartnoma o'zi tanlanadi.",
                L.click('#view .settings-body .tbl tbody tr:first-child [data-act="pay-new"]', "Toʻlov", side="left"))
    await L.wait_for(f("amount"))
    await L.say("Shartnoma va joriy balans tayyor. Summani yozamiz.",
                L.show('.overlay:last-child [data-f="bal"]', "Balans", side="below", hold=0.5),
                L.type(f("amount"), "250000", "Summa", delay=90))
    if await L.exists('.overlay:last-child [data-f="accountant"]:not([hidden]) select'):
        await L.say("Hisobchi sifatida o'zingizni tanlaysiz.", L.choose(f("accountant", "select"), text="Namuna", label="Hisobchi"))
    await L.say("«Qabul qilish va chek».", L.click(SAVE, "Qabul qilish va chek", side="above"))
    await L.show_pdf("Toʻlov cheki")
    await L.say("Chek tayyor. Talaba to'liq to'lagach, u tavsiya ro'yxatidan o'zi chiqib ketadi.")
    await L.hide_image()
    await L.say("Ba'zan talaba to'lagan bo'ladi, lekin ro'yxatda qoladi — masalan, rahbarga to'g'ridan-to'g'ri to'lagan. Shunda «✓ To'lov qilgan» tugmasini bosasiz.",
                L.click('#view .settings-body .tbl tbody tr:first-child [data-act="due-dismiss"]', "✓ Toʻlov qilgan", side="left"))
    await L.wait(1.0)
    await L.say("Talaba shu oy uchun ro'yxatdan va Telegram eslatmalaridan olib tashlandi. Keyingi oy yana chiqadi.")
    await L.say("Olib tashlanganlarni ko'rish uchun filtrdan «Olib tashlanganlar»ni tanlaymiz.",
                L.choose('select[data-filter="debtors:dismissed"]', "1", label="Olib tashlanganlar"))
    await L.wait(1.0)
    await L.say("Adashib bosgan bo'lsangiz, «Qaytarish» tugmasi bilan tavsiyaga qaytarasiz.",
                L.show('#view [data-act="due-restore"]', "Qaytarish", side="left"))
    await L.say("Filtrni tavsiyadagilarga qaytaramiz.",
                L.choose('select[data-filter="debtors:dismissed"]', "", label="Tavsiyadagilar"))
    await L.wait(1.0)
    await L.clear()
    await L.say("Endi SMS eslatma. SMS markazning qabul telefonidan, uning SIM kartasidan yuboriladi.")
    await L.say("Bitta talabaga yuborish uchun qatordagi xat belgisini bosamiz.",
                L.click('#view .settings-body .tbl tbody tr:first-child [data-act="due-sms"]', "SMS", side="left"))
    await L.wait_for(f("text", "textarea"))
    await L.say("SMS talabaning hamma raqamiga ketadi: birinchi, ikkinchi telefon va vasiyga.",
                L.show('.overlay:last-child [data-f="who"]', "Kimga", side="below"))
    await L.say("Qolip — tayyor matn. Qoliplarni «Qo'ng'iroqlar va SMS» bo'limida yozasiz.",
                L.show('.overlay:last-child [data-f="template"]', "Qolip", side="below"))
    await L.say("Matndagi jingalak qavsdagi so'zlar o'rniga talabaning ismi, oy, summa va muddat o'zi qo'yiladi.",
                L.show('.overlay:last-child [data-f="text"]', "Matn", side="below"))
    await L.say("Pastda — shu talaba uchun tayyor SMS namunasi va nechta SMS bo'lishi. Apostrof va kirill harflari SMS sonini oshiradi.",
                L.show('.overlay:last-child [data-f="preview"]', "Namuna", side="above"))
    await L.say("Bu belgi yoqiq bo'lsa, shu oy SMS olgan raqamga qayta yuborilmaydi.",
                L.show('.overlay:last-child [data-f="skip_sent"]', "Takrorlanmasin", side="above"))
    await L.say("«Davom etish»ni bosamiz.", L.click(SAVE, "Davom etish", side="above"))
    await L.wait_for(".overlay:last-child [data-ok]")
    await L.say("Tizim oxirgi marta so'raydi: nechta talaba, nechta raqam va jami nechta SMS ketadi.",
                L.show(".overlay:last-child .modal-body", "Tekshiring", side="below"))
    await L.say("Hammasi to'g'ri bo'lsa — «Yuborish».", L.click(".overlay:last-child [data-ok]", "Yuborish", side="above"))
    await L.wait(1.2)
    await L.say("SMS navbatga qo'yildi. Telefon uni bir necha daqiqada yuboradi. «SMS» ustunida holati ko'rinadi.",
                L.show("#view .settings-body .tbl tbody tr:first-child td[data-label='SMS']", "SMS holati", side="left"))
    await L.say("Tepadagi «SMS yuborish» tugmasi esa ro'yxatda ko'rinib turgan hamma talabaga yuboradi. Shuning uchun avval daraxt yoki filtr bilan kerakli guruhni tanlang.",
                L.show('#view .page-head [data-act="due-sms-all"]', "Hammaga SMS", side="below"))
    await L.say("SMS faqat siz «Yuborish»ni bosganingizda ketadi — tizim o'zicha hech kimga SMS yubormaydi.")
    await L.clear()
    await L.say("Ikkinchi tab — «Qarz (davomat bo'yicha)». Bu haqiqiy qarz: o'tilgan darslar uchun hisoblangan summadan to'lovlar ayirilgan.",
                L.click('#view .tabs a[href*="tab=debt"]', "Haqiqiy qarz", side="below", wait=1.5))
    await L.say("Bu yerda ham daraxt, jami qarz va har bir qarzdor. Shartnomani bossangiz, qarz qanday hisoblangani ochiladi.",
                L.show("#view .settings-body", "Qarzdorlar", side="left"))
    await L.say("Har ikkala tabda ham «Excel» tugmasi bilan ro'yxatni faylga yuklash mumkin.",
                L.show('#view .page-head [data-act="debtors-csv"]', "Excel", side="below"))
    await L.clear()
    await L.say("Eslatma: ertalab soat sakkiz yarimda bot sizga bugungi to'lov rejasini, har darsdan o'n daqiqa oldin esa shu guruhdagi qarzdorlarni yuboradi.")
    await outro(L, "Davomat")
