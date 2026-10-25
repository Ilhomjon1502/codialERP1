from common import lesson, outro


@lesson("02", "bosh_sahifa", "Bosh sahifa va dars jadvali")
async def l02(L):
    await L.card("2-dars", "Bosh sahifa va dars jadvali", "Kun boshida birinchi qaraladigan ekran",
                 ["Ogohlantirishlar", "Bugungi toʻlovlar va tushum", "Qarzdorlik va faol talabalar",
                  "Dars jadvali: kunlar va xonalar", "Guruhni jadvaldan boshqarish", "Boʻsh joyga yangi guruh"],
                 text="Ikkinchi darsda bosh sahifani o'rganamiz. Tizimga kirganingizda birinchi shu sahifa ochiladi.")
    await L.uncard()
    await L.say("Tepada salomlashuv, bugungi sana va lavozimingiz yoziladi.", L.show("#view .page-head", "Salomlashuv", side="below"))
    if await L.exists("#view .alert"):
        await L.say("Sariq yoki qizil bloklar — ogohlantirishlar, masalan sizga berilgan ochiq topshiriqlar. Havolani bossangiz, kerakli bo'lim ochiladi.",
                    L.show("#view .alert", "Ogohlantirish", side="below"))
    await L.say("Keyin kartochkalar: bular kunning eng muhim raqamlari.", L.show("#view .stats", "Asosiy raqamlar", side="below", hold=0.6))
    await L.say("«Bugungi to'lovlar» — bugun qabul qilingan pul: naqd va naqdsiz alohida.",
                L.show("""#view .stat:has-text("Bugungi to'lovlar")""", "Bugungi toʻlovlar", side="below"))
    await L.say("«Shu oy tushum» — oy boshidan beri tushgan barcha to'lovlar.",
                L.show('#view .stat:has-text("Shu oy tushum")', "Oylik tushum", side="below"))
    await L.say("«Tasdiq kutmoqda» — rahbar tasdiqlashi kerak bo'lgan to'lov va chegirmalar soni.",
                L.show('#view .stat:has-text("Tasdiq kutmoqda")', "Tasdiq kutmoqda", side="below"))
    await L.say("«Faol talabalar» — hozir o'qiyotganlar soni va faol guruhlar.",
                L.show('#view .stat:has-text("Faol talabalar")', "Faol talabalar", side="below"))
    await L.say("«Jami qarzdorlik» — barcha qarzdorlarning umumiy qarzi va ular soni. Qizil rangda, chunki bu bilan ishlash kerak.",
                L.show('#view .stat:has-text("Jami qarzdorlik")', "Qarzdorlik", side="below"))
    await L.say("Har bir kartochka bosiladi: masalan qarzdorlikni bossangiz, Qarzdorlar ro'yxati ochiladi.")
    await L.clear()
    await L.say("Pastda — dars jadvali. U guruhlardan avtomatik tuziladi: qaysi xonada, soat nechada, qaysi guruh.",
                L.scroll(".sched", wait=1.0), L.show(".sched .sched-wrap", "Dars jadvali", side="above"))
    await L.say("Tepada hafta kunlari. Bugungi kun nuqta bilan belgilangan, yonidagi son — shu kundagi darslar soni.",
                L.show(".sched-days", "Hafta kunlari", side="below"))
    await L.say("Boshqa kunni ko'rish uchun shu kunni bosasiz. Masalan, dushanbani tanlaymiz.",
                L.click('[data-act="sched-day"][data-id="1"]', "Dushanba", side="below", wait=1.0))
    await L.say("Jadvalni ustozlar bo'yicha ham ko'rish mumkin: «Ustozlar» tugmasini bosamiz.",
                L.click('[data-act="sched-by"][data-id="teacher"]', "Ustozlar boʻyicha", side="below", wait=1.0))
    await L.say("Endi har bir qator — bitta ustoz. Bu ustoz qachon band, qachon bo'shligini ko'rsatadi.",
                L.show(".sched .sched-wrap", "Ustozlar jadvali", side="above"))
    await L.say("Yana xonalar ko'rinishiga qaytamiz.",
                L.click('[data-act="sched-by"][data-id="room"]', "Xonalar boʻyicha", side="below", wait=1.0))
    await L.say("Har bir rangli blok — bitta guruh: nomi, talabalar soni va ustozi. Och yashil blok — hali boshlanmagan, rejadagi guruh.",
                L.show(".sched-b", "Guruh", side="below"))
    await L.say("Qizil blok chiqsa — ikki guruhning vaqti bir xonada ustma-ust tushgan. Buni darhol tuzatish kerak.")
    await L.js("""() => { const b = [...document.querySelectorAll('.sched-b:not(.plan)')].find((x) => /👥 [1-9]/.test(x.textContent));
        if (b) b.setAttribute('data-tv-pick', '1'); }""")
    await L.say("Guruh blokini bosamiz.", L.click("[data-tv-pick]", "Guruhni bosamiz", side="below"))
    await L.wait_for(".overlay .modal")
    await L.say("Guruhni boshqarish oynasi ochildi: holati, dars kunlari, vaqti, xonasi, ustozi va o'quvchilar soni.",
                L.show(".overlay .modal-body > p", "Guruh maʼlumotlari", side="below"))
    await L.say("Tugmalar: kun, vaqt, xona va ustozni o'zgartirish; to'liq tahrirlash; jurnal va guruh sahifasi.",
                L.show('.overlay .modal-body .row:has([data-m="sched"])', "Amallar", side="below"))
    if await L.exists(".overlay .modal-body .tbl-wrap"):
        await L.say("Pastda guruhdagi o'quvchilar ro'yxati va balansi. Qizil ism — qarzdor. Bu yerdan yangi o'quvchi ham qo'shish mumkin.",
                    L.scroll(dy=300), L.show(".overlay .modal-body .tbl-wrap", "Oʻquvchilar", side="above"))
    await L.close_modal("Yopish")
    await L.say("Jadvaldagi bo'sh joyni bossangiz, shu xona va vaqtga yangi guruh ochish formasi chiqadi. Bu haqda guruhlar darsida gaplashamiz.",
                L.show(".sched-track.addable", "Boʻsh joy — yangi guruh", side="below"))
    await L.clear()
    await outro(L, "Topshiriqlar")
