from common import SAVE, f, lesson, option, outro


@lesson("12", "pul", "Xarajatlar, o'tkazmalar va g'aznalar")
async def l12(L):
    await L.card("12-dars", "Xarajatlar, oʻtkazmalar va gʻaznalar", "Markaz pulining harakati",
                 ["Xarajat kiritish", "Xarajatlar hisoboti", "Gʻazna qoldigʻi", "Pul harakatlari jurnali",
                  "Gʻaznalar orasida oʻtkazma", "Oʻtkazmani tasdiqlash"],
                 text="O'n ikkinchi darsda markaz pulining harakatini o'rganamiz: xarajatlar, g'aznalar va ular orasidagi o'tkazmalar.")
    await L.uncard()
    await L.say("G'azna — pul turadigan joy: kassa yoki karta. Har bir to'lov g'aznaga kiradi, har bir xarajat g'aznadan chiqadi.")
    await L.nav("expenses", "Xarajatlar")
    await L.say("Xarajatlar sahifasi. Har qatorda: sana, kategoriya, nomi, soni va narxi, jami, g'azna va hisob davri.",
                L.show("#view .tbl thead", "Ustunlar", side="below"))
    await L.say("Markaz biror narsa sotib olsa yoki to'lasa, xarajat kiritamiz. «Xarajat qo'shish»ni bosamiz.",
                L.click('[data-act="exp-new"]', "Xarajat qoʻshish", side="below"))
    await L.wait_for(f("category", "select"))
    await L.say("Sana — bugun.", L.show('[data-f="date"]', "Sana", side="below"))
    await L.say("Kategoriya — xarajat turi: ijara, internet, kommunal, xo'jalik va hokazo.",
                L.choose(f("category", "select"), text="Xo'jalik", label="Kategoriya"), L.wait(1.2))
    await L.say("Nomi — nima olindi. Shu kategoriyada oldin yozilgan nomlar taklif qilinadi.",
                L.fill(f("name"), "Qog'oz A4", "Nomi"))
    await L.say("Soni va bitta narxi. Jami summa o'zi hisoblanadi.",
                L.type(f("quantity"), "2", "Soni"), L.type(f("price"), "45000", "Narxi", delay=90))
    await L.show('[data-f="total"]', "Jami", side="above", hold=1.0)
    await L.say("Qaysi pul bilan to'landi — naqd, karta yoki bank. G'azna avtomatik tanlanadi.",
                L.show('.overlay:last-child [data-f="cash_type"] button[data-val="CASH"]', "Naqd", side="above"))
    if await L.exists('.overlay:last-child [data-f="cashier"]:not([hidden]) select'):
        await L.choose(f("cashier", "select"), text="Namuna", label="Gʻaznachi")
    await L.say("Ko'k yozuv g'aznadagi qoldiqni ko'rsatadi. Qoldiqdan ko'p xarajat kiritib bo'lmaydi.",
                L.show('.overlay:last-child [data-f="bal"]', "Gʻaznadagi pul", side="above"))
    await L.say("«Saqlash».", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("Xarajat ro'yxatga qo'shildi va g'azna qoldig'idan ayirildi. Xato bo'lsa, faqat shu kuni tuzatish yoki o'chirish mumkin.",
                L.show("#view .tbl tbody tr:first-child", "Yangi xarajat", side="below"))
    await L.say("«Oy → kategoriya» tabida xarajatlar oy va kategoriyalar bo'yicha jamlanadi.",
                L.click('#view .tabs a[href*="tab=cat"]', "Oy → kategoriya", side="below", wait=1.5))
    await L.show("#view .group-block", "Oylik jamlama", side="below", hold=1.5)
    await L.clear()
    await L.say("Endi g'aznalar.", L.nav("accounts", "Gʻaznalar"))
    await L.say("Har bir g'azna kartochkasida: joriy qoldiq, pul turlari bo'yicha qoldiq va mas'ul xodimlar.",
                L.show("#view .gcard", "Gʻazna", side="right"))
    await L.say("To'q sariq «tasdiqlanmagan» — karta to'lovlari, rahbar tasdiqlaguncha qoldiqqa qo'shilmaydi.")
    await L.say("G'aznani ochamiz.", L.click("#view .gcard", "Gʻaznani ochamiz", side="right"))
    await L.wait_for("#view .tbl")
    await L.say("Bu — pul harakatlari jurnali: har bir to'lov, xarajat, oylik va o'tkazma. Kirim yashil, chiqim qizil.",
                L.show("#view .tbl thead", "Jurnal", side="below"))
    await L.say("Kassadagi naqd pul shu yerdagi qoldiq bilan teng bo'lishi kerak. Har kuni oxirida sanab, solishtirib qo'ying.",
                L.show("#view .stats", "Qoldiq", side="below"))
    await L.clear()
    await L.say("Kassadagi pulni boshqa g'aznaga — masalan, rahbarga topshirish uchun «Ichki pul oqimi»dan foydalanamiz.",
                L.nav("transfers", "Ichki pul oqimi"))
    await L.say("«O'tkazma» tugmasini bosamiz.", L.click('[data-act="tr-new"]', "Oʻtkazma", side="below"))
    await L.wait_for(f("amount"))
    await L.say("Yuboruvchi g'azna — sizning kassangiz. O'tkazma faqat naqd pul uchun.",
                L.show('[data-f="cash_type"]', "Naqd", side="below"))
    if await L.exists('.overlay:last-child [data-f="sender_cashier"]:not([hidden]) select'):
        await L.say("Yuboruvchi g'aznachi — pulni topshirayotgan xodim, ya'ni siz.",
                    L.choose(f("sender_cashier", "select"), text="Namuna", label="Yuboruvchi"))
    cash = await L.js("""() => { const h = document.querySelector('.overlay:last-child [data-f="amount"] .help:not(.money-hint)');
        const m = h && h.textContent.match(/([\\d\\s\\u00a0]+) so/); return m ? Number(m[1].replace(/\\D/g, '')) : 0; }""") or 0
    await L.say("Summa avtomatik — kassadagi hamma naqd pul. Pastida g'aznada qancha naqd borligi yozilgan.",
                L.show('.overlay:last-child [data-f="amount"]', "Summa", side="below"))
    val = await option(L, '.overlay:last-child [data-f="receiver"] select')
    await L.say("Qabul qiluvchi g'azna.", L.choose(f("receiver", "select"), val, label="Qabul qiluvchi"))
    if await L.exists('.overlay:last-child [data-f="receiver_cashier"]:not([hidden]) select'):
        val = await option(L, '.overlay:last-child [data-f="receiver_cashier"] select')
        await L.say("Pulni qabul qiladigan xodim.", L.choose(f("receiver_cashier", "select"), val, label="Qabul qiluvchi"))
    await L.say("Izoh.", L.type(f("comment", "textarea"), "Kunlik tushum topshirildi", "Izoh", delay=40, side="above"))
    await L.say("Kassadagidan ko'p summa yozib, saqlab ko'ramiz.",
                L.type(f("amount"), str(cash + 1000000), "Koʻp summa", delay=80),
                L.click(SAVE, "Saqlash", side="above"))
    await L.say("Tizim ruxsat bermadi: g'aznada buncha naqd pul yo'q. Bu xato pul chiqib ketishidan himoya qiladi.",
                L.show('.overlay:last-child [data-f="amount"] .err', "Gʻaznada buncha pul yoʻq", side="below"))
    await L.say("Shuning uchun kassadagi summani yozamiz.",
                L.type(f("amount"), str(cash or 5000), "Summa", delay=80))
    await L.say("«Saqlash».", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("O'tkazma «Tasdiqlashga» holatida. Pulni olgan xodim «Qabul qildim» tugmasini bosmaguncha ikkala g'azna qoldig'i ham o'zgarmaydi.",
                L.show('#view .tbl tbody tr:has([data-act="tr-edit"])', "Tasdiqlashga", side="below"))
    await L.say("Sizga pul o'tkazishsa, shu ro'yxatda yoki «Tasdiqlashlar»da «Qabul qildim» tugmasi chiqadi. Pulni sanab olib, keyin bosing.")
    await L.say("Tasdiqlanmaguncha o'tkazmani qalam bilan tuzatish yoki o'chirish mumkin.",
                L.show('#view .tbl tbody [data-act="tr-edit"]', "Tuzatish", side="left"))
    await L.clear()
    await outro(L, "Ota-onalar bilan aloqa va Excel")
