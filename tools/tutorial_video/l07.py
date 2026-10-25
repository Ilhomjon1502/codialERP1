from common import MODAL, SAVE, f, lesson, outro

PICK_DEBTOR = """(n) => { const s = document.querySelector('.overlay:last-child [data-f="contract"] select');
  const o = [...s.options].filter(o => /balans [1-9]/.test(o.textContent) && !/nofaol/.test(o.textContent)); return o[n] ? o[n].value : null; }"""


async def pick_accountant(L):
    if await L.exists('.overlay:last-child [data-f="accountant"]:not([hidden]) select'):
        await L.say("Hisobchi — pulni qabul qilgan xodim. O'zingizni tanlaysiz.",
                    L.choose(f("accountant", "select"), text="Namuna", label="Hisobchi"))


@lesson("07", "tolovlar", "To'lov qabul qilish va tasdiqlashlar")
async def l07(L):
    await L.card("7-dars", "Toʻlov qabul qilish", "Naqd va naqdsiz toʻlov, chegirma, chek va tasdiqlashlar",
                 ["Toʻlovlar roʻyxati", "Naqd toʻlov qabul qilish", "Chek (PDF)", "Karta orqali toʻlov",
                  "Chegirma va uning limiti", "Tasdiqlashlar boʻlimi"],
                 text="Yettinchi darsda eng muhim ishlardan biri — to'lov qabul qilishni o'rganamiz.")
    await L.uncard()
    await L.nav("payments", "Toʻlovlar")
    await L.say("To'lovlar sahifasi. To'lovlar oy va kun bo'yicha guruhlangan, har birida jami summa.",
                L.show("#view .group-block h3", "Oy jami", side="below", hold=0.6),
                L.show("#view .day-h", "Kun jami", side="below"))
    await L.say("Har bir qatorda: chek raqami, shartnoma, summa, to'lov turi, chegirma, g'azna va pulni olgan xodim.",
                L.show("#view .group-block .tbl thead", "Toʻlov qatorlari", side="below"))
    await L.say("Qidiruvga talaba ismi yoki chek raqamini yozasiz; oy va to'lov turi bo'yicha filtrlash mumkin.",
                L.show("#view .filters", "Filtrlar", side="below"))
    await L.clear()
    await L.say("Talaba pul olib keldi. «To'lov qabul qilish» tugmasini bosamiz.",
                L.click('#view .page-head [data-act="pay-new"]', "Toʻlov qabul qilish", side="below"))
    await L.wait_for(f("contract", "select"))
    val = await L.js(PICK_DEBTOR, 0)
    await L.say("Avval shartnomani tanlaymiz. Ro'yxatda har bir talabaning guruhi va joriy balansi yozilgan.",
                L.choose(f("contract", "select"), val, label="Shartnoma"))
    await L.say("Tanlangach, joriy balans ko'rinadi: qizil — talaba qarzdor.",
                L.show('.overlay:last-child [data-f="bal"]', "Joriy balans", side="below"))
    await L.say("To'lov miqdorini yozamiz. Pastida summa so'mda o'qilishi oson ko'rinishda chiqadi.",
                L.type(f("amount"), "300000", "Toʻlov miqdori", delay=90))
    await L.say("To'lov shakli: naqd, karta yoki bank. Naqd pul — «Naqd».",
                L.show('.overlay:last-child [data-f="cash_type"] button[data-val="CASH"]', "Naqd", side="below"))
    await L.say("G'azna avtomatik tanlanadi — siz mas'ul bo'lgan kassa. Naqd pul shu g'aznaga tushadi.")
    await pick_accountant(L)
    await L.say("Sana — faqat bugungi kun. O'tgan sana bilan to'lovni faqat rahbariyat kiritadi.",
                L.show('.overlay:last-child [data-f="date"]', "Sana", side="above"))
    await L.say("Izoh ixtiyoriy, masalan: kim olib keldi.",
                L.type(f("comment", "textarea"), "Onasi olib keldi", "Izoh", delay=40, side="above"))
    await L.say("«Qabul qilish va chek» tugmasini bosamiz.", L.click(SAVE, "Qabul qilish va chek", side="above"))
    await L.show_pdf("Toʻlov cheki (PDF)")
    await L.say("To'lov saqlandi va chek avtomatik ochildi. Chekda: raqami, sana, talaba, kurs, summa va qolgan balans.")
    await L.say("Chekni chop etib berish yoki ota-onaga Telegram orqali yuborish mumkin.")
    await L.hide_image()
    await L.say("Yangi to'lov ro'yxatning eng tepasida. «Chek» tugmasi bilan chekni istalgan vaqtda qayta ochish mumkin.",
                L.show('#view .group-block .tbl tbody tr:first-child', "Yangi toʻlov", side="below"))
    await L.say("Xato kiritsangiz, qalam belgisi bilan tuzatasiz yoki savatcha bilan o'chirasiz. Buni faqat to'lov kuni qilish mumkin.",
                L.show('#view .group-block .tbl tbody tr:first-child [data-act="pay-edit"]', "Tuzatish", side="left"))
    await L.clear()
    await L.say("Endi karta orqali to'lov va chegirmani ko'ramiz. Yana «To'lov qabul qilish»ni bosamiz.",
                L.click('#view .page-head [data-act="pay-new"]', "Toʻlov qabul qilish", side="below"))
    await L.wait_for(f("contract", "select"))
    val = await L.js(PICK_DEBTOR, 1)
    await L.say("Boshqa talabani tanlaymiz.", L.choose(f("contract", "select"), val, label="Shartnoma"))
    await L.say("Summani yozamiz.", L.type(f("amount"), "400000", "Summa", delay=90))
    await L.say("Talaba kartadan o'tkazdi — «Karta»ni tanlaymiz.", L.seg("cash_type", "CARD", "Karta", side="below"))
    await L.say("Sariq yozuvga e'tibor bering: naqdsiz to'lov rahbar tasdiqlamaguncha g'azna balansiga qo'shilmaydi.",
                L.show('.overlay:last-child [data-f="nc_note"]', "Tasdiqlash kerak", side="below"))
    # Shu kurs uchun mavjud birinchi chegirma turi va uning limiti («… (max 100 000)»)
    disc = await L.js("""() => { const s = document.querySelector('.overlay:last-child [data-f="discount_type"] select');
        const o = s && [...s.options].find((o) => o.value); if (!o) return null;
        const m = o.textContent.match(/max ([\\d\\s\\u00a0]+)/); return { v: o.value, max: m ? Number(m[1].replace(/\\D/g, '')) : 0 }; }""") or {}
    over, ok = str((disc.get("max") or 100000) + 50000), str(disc.get("max") or 100000)
    await L.say("Talabaga chegirma beramiz. Chegirma turini tanlaymiz — yonida eng ko'p miqdori yozilgan.",
                L.choose(f("discount_type", "select"), disc.get("v"), label="Chegirma turi"))
    await L.say("Chegirma summasini limitdan ko'p yozsak nima bo'ladi? Masalan, limitdan ellik ming ortiq.",
                L.type(f("discount"), over, "Chegirma", delay=90))
    await L.say("«Saqlash»ni bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.say("Tizim ruxsat bermadi: bu chegirma turida limitdan ortiq kiritib bo'lmaydi.",
                L.show('.overlay:last-child [data-f="discount"] .err', "Limitdan oshdi", side="below"))
    await L.say("Summani limit ichida qilib tuzatamiz.", L.type(f("discount"), ok, "Chegirma", delay=90))
    await L.say("Chegirma ham tasdiqlashga yuboriladi.", L.show('.overlay:last-child [data-f="d_note"]', "Tasdiqlashga", side="above"))
    await pick_accountant(L)
    await L.say("Saqlaymiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("To'lov ro'yxatda «Tasdiqlashga» belgisi bilan turibdi. Tasdiqlanmaguncha chek chiqmaydi.",
                L.show('#view .group-block .tbl tbody tr:first-child', "Tasdiqlashga", side="below"))
    await L.clear()
    await L.say("Tasdiq kutayotgan ishlar «Tasdiqlashlar» bo'limida. Unga menyudan yoki yuqoridagi qo'ng'iroqcha orqali o'tasiz.",
                L.show("#top-bell", "Qoʻngʻiroqcha", side="below", hold=0.6),
                L.nav("approvals", "Tasdiqlashlar"))
    await L.say("Tablar: chegirmalar, naqdsiz to'lovlar, o'tkazmalar, qoldirilgan darslar va oydagi dars soni. Yonidagi son — rahbar tasdiqlashi kerak bo'lganlar, sizda u nol ko'rinadi.",
                L.show("#view .tabs", "Tasdiq turlari", side="below"))
    await L.say("Mana bizning chegirmamiz. Uni Admin yoki Bosh menejer tasdiqlaydi — siz faqat holatini kuzatasiz.",
                L.show("#view .tbl tbody tr:first-child", "Chegirma", side="below"))
    await L.say("«Naqdsiz to'lovlar» tabida — karta to'lovi. Tasdiqlangach summa g'azna balansiga qo'shiladi.",
                L.click('#view .tabs a[href*="tab=nc"]', "Naqdsiz toʻlovlar", side="below", wait=1.2))
    await L.say("Izoh ustunida nima yozganingiz ko'rinadi — shuning uchun karta to'lovida kimdan va qaysi kartadan kelganini izohga yozing.",
                L.show("#view .tbl", "Naqdsiz toʻlovlar", side="above"))
    await L.clear()
    await outro(L, "Qarzdorlar, to'lovga tavsiya va SMS")
