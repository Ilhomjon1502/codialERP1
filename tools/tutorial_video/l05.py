from common import MODAL, SAVE, f, lesson, outro, tomorrow_10

LEAD = '.kanban .kcol:nth-child(2) .kcard:has-text("Backend")'


@lesson("05", "lidlar_2", "Lid bilan ishlash: boshidan shartnomagacha")
async def l05(L):
    await L.card("5-dars", "Lid bilan ishlash", "Birinchi qoʻngʻiroqdan shartnomagacha",
                 ["Lid kartochkasi", "Izoh yozish", "Qayta bogʻlanish vaqti", "Sinov darsiga yozish",
                  "Talaba maʼlumotlarini toʻldirish", "Shartnoma tuzish"],
                 text="Beshinchi darsda bitta lidni boshidan oxirigacha olib boramiz: izoh, qayta bog'lanish, sinov darsi va shartnoma.")
    await L.uncard()
    await L.nav("leads", "Lidlar")
    await L.say("Ikkinchi ustundagi lidni bosamiz.", L.click(LEAD, "Lidni ochamiz", side="right"))
    await L.wait_for(MODAL + " .dl")
    await L.say("Lid kartochkasi ochildi. Tepada — joriy status va shartnoma holati.",
                L.show(MODAL + " .detail-top", "Status", side="below"))
    await L.say("Keyin ma'lumotlar: telefonlar, kurs, manba, hafta kunlari, yosh guruhi va kim qo'shgani.",
                L.show(MODAL + " .dl", "Maʼlumotlar", side="right"))
    await L.say("Telefon raqamini telefonda bossangiz, darhol qo'ng'iroq boshlanadi.")
    await L.say("Pastda — statusni o'zgartirish tugmalari. Kerakli bosqichni bossangiz, lid shu bosqichga o'tadi.",
                L.show(MODAL + " .seg.wrap", "Statusni oʻzgartirish", side="above"))
    if await L.exists(MODAL + " #lead-calls h4"):
        await L.say("Bu yerda shu raqam bilan bo'lgan qo'ng'iroqlar va SMS tarixi ko'rinadi — kim, qachon gaplashgani.",
                    L.show(MODAL + " #lead-calls", "Qoʻngʻiroqlar tarixi", side="above"))
    await L.say("Har bir suhbatdan keyin izoh yozing. Izoh maydoniga yozamiz.",
                L.type(MODAL + " #lc-text", "Qo'ng'iroq qildim, ertaga javob beradi", "Izoh", delay=40, side="above"))
    await L.say("«Qo'shish» tugmasini bosamiz.", L.click(MODAL + " #lc-add", "Qoʻshish", side="above"))
    await L.wait_for(MODAL + " .comments li")
    await L.say("Izoh saqlandi: kim yozgani va vaqti bilan. Keyingi xodim lid tarixini shu yerdan o'qiydi.",
                L.show(MODAL + " .comments", "Izohlar", side="above"))
    await L.clear()
    await L.say("Talaba «ertaga javob beraman» dedi. Statusni «1. Qayta bog'lanishga» o'tkazamiz.",
                L.click(MODAL + ' .seg.wrap button[data-status="1"]', "1-bosqich", side="above"))
    await L.wait_for(f("callback_at"))
    await L.say("Tizim qayta bog'lanish sana va vaqtini so'raydi. Odatda ertangi kun soat o'n qo'yiladi.",
                L.fill(f("callback_at"), tomorrow_10(), "Sana va vaqt", side="below"))
    await L.say("Shu vaqt kelganda bot sizga «qayta bog'lanish vaqti keldi» deb xabar beradi. Xabardagi tugmalar: qo'ng'iroq qilindi, bir soatga yoki ertaga surish.")
    await L.say("«Saqlash»ni bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait_for(MODAL + " .dl")
    await L.say("Kartochkada endi qayta bog'lanish vaqti ko'rinadi. Uni «O'zgartirish» tugmasi bilan surish mumkin.",
                L.show(MODAL + " .dl [data-cb]", "Qayta bogʻlanish", side="right"))
    await L.say("Ertasi kuni qo'ng'iroq qildik — talaba sinov darsiga kelishga rozi bo'ldi. Sinov darsiga yozish uchun «Tahrirlash»ni bosamiz.",
                L.click(MODAL + " [data-edit]", "Tahrirlash", side="above"))
    await L.wait_for(f("status", "select"))
    await L.say("Statusni «3. Sinov darsga yozildi» qilamiz.",
                L.choose(f("status", "select"), "3", label="Status"))
    await L.say("Endi guruh maydoni chiqdi: shu kursning faol yoki rejadagi guruhlari. Sinov darsi bo'ladigan guruhni tanlaymiz.",
                L.choose(f("group", "select"), text="Backend", label="Guruh"))
    await L.say("Sinov dars kuni — standart bugun. Kerak bo'lsa boshqa sanani qo'yasiz.",
                L.show('[data-f="demo_date"]', "Sinov dars kuni", side="above"))
    await L.say("«Saqlash»ni bosamiz. Lid voronkaning uchinchi ustuniga o'tadi, ertalabki rejada «sinov darsiga keladiganlar» ro'yxatida chiqadi.",
                L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("Sinov darsi kuni talaba keldi. Kartochkani yana ochamiz.",
                L.click('.kanban .kcol:nth-child(3) .kcard:has-text("Backend")', "Lid", side="right"))
    await L.wait_for(MODAL + " .dl")
    await L.say("Statusni «4. Sinov darsga qatnashdi» qilamiz.",
                L.click(MODAL + ' .seg.wrap button[data-status="4"]', "4-bosqich", side="above"))
    await L.wait_for(MODAL + ' .seg.wrap button[data-status="4"].on')
    await L.say("Talaba o'qishga qaror qildi. «5. O'qishni boshladi» ni bosamiz.",
                L.click(MODAL + ' .seg.wrap button[data-status="5"]', "5-bosqich", side="above"))
    await L.wait_for(MODAL + ' .seg.wrap button[data-status="5"].on')
    await L.say("Sariq ogohlantirish chiqdi: shartnoma uchun talabaning to'liq ma'lumotlari kerak — tug'ilgan sanasi va vasiysi.",
                L.show(MODAL + " .alert.warn", "Maʼlumot yetishmaydi", side="below"))
    await L.say("Shuning uchun «Shartnoma tuzish» tugmasi hozircha o'chiq. Avval «Talaba ma'lumotlarini to'ldirish»ni bosamiz.",
                L.show(MODAL + " [data-contract]", "Hozircha oʻchiq", side="above", hold=0.8),
                L.click(MODAL + " [data-student]", "Maʼlumotlarni toʻldirish", side="above"))
    await L.wait_for(f("birth_date"))
    await L.say("Ism, familiya va telefonlar liddan olingan. Sharif ixtiyoriy: kiritsangiz, nuqtasiz va kamida uch harf.",
                L.type(f("father_name"), "Anvarovich", "Sharif", side="below"))
    await L.say("Tug'ilgan sana majburiy.", L.fill(f("birth_date"), "2008-05-14", "Tugʻilgan sana", side="below"))
    await L.say("Vasiy — ota yoki ona. Bazada bo'lsa ro'yxatdan tanlanadi. Yangi bo'lsa, «Yangi vasiy qo'shish» belgisini qo'yamiz.",
                L.click(f("new_parent"), "Yangi vasiy", side="right"))
    await L.say("Vasiy kim bo'lishi majburiy: ota, ona, aka, opa va hokazo.",
                L.choose(f("p_relation", "select"), "Ona", label="Kim boʻladi"))
    await L.say("Vasiyning telefon raqami.", L.type(f("p_phone"), "901234567", "Vasiy telefoni"))
    await L.say("«Saqlash»ni bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait_for(MODAL + " [data-contract]:not([disabled])")
    await L.say("Endi «Shartnoma tuzish» tugmasi yoqildi. Uni bosamiz.",
                L.click(MODAL + " [data-contract]", "Shartnoma tuzish", side="above"))
    await L.wait_for("#view .back")
    await L.say("Shartnoma tuzildi va uning sahifasi ochildi: talaba, kurs, guruh va balans. Shartnoma raqami avtomatik beriladi.",
                L.show("#view .page-head", "Yangi shartnoma", side="below"))
    await L.say("Shartnoma boshlanish sanasi — sinov dars kuni. Shu kundan boshlab har bir dars uchun hisob yuritiladi.")
    await L.clear()
    await L.keynote("Lid → Shartnoma", "Izoh · Qayta bogʻlanish · Sinov darsi · Maʼlumotlar · Shartnoma",
                    text="Xulosa: har bir suhbatdan keyin izoh yozing, qayta bog'lanish vaqtini qo'ying, sinov darsiga guruh bilan yozing va o'qishni boshlaganda shartnoma tuzing.")
    await outro(L, "Shartnomalar")
