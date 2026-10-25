from common import MODAL, SAVE, f, lesson, option, outro


@lesson("10", "guruhlar", "Guruhlar")
async def l10(L):
    await L.card("10-dars", "Guruhlar", "Guruh ochish, toʻlishi va davomat jurnali",
                 ["Faol, rejadagi va nofaol guruhlar", "Toʻlish ranglari", "Guruh sahifasi va jurnal",
                  "Yangi guruh ochish", "Xona va ustoz bandligi", "Jadvaldan guruh qoʻshish"],
                 text="O'ninchi darsda guruhlarni o'rganamiz: ularni ko'rish, yangi guruh ochish va davomat jurnali.")
    await L.uncard()
    await L.nav("groups", "Guruhlar")
    await L.say("Tablar: «Faol» — dars ketayotgan guruhlar, «Rejada» — hali boshlanmagan, «Nofaol» — tugagan guruhlar.",
                L.show("#view .tabs", "Holat", side="below"))
    await L.say("Har bir kartochka — bitta guruh: nomi, dars kunlari, vaqti, xonasi, ustozi va to'lishi.",
                L.show("#view .gcard", "Guruh", side="right"))
    await L.say("Guruh nomining rangi — to'lish holati: qizil — yomon, to'q sariq — o'rtacha, ko'k — yaxshi, yashil — zo'r.")
    await L.say("Pastdagi chiziq va raqamlar: nechta talaba bor, nechta bo'sh o'rin qolgan. Bo'sh o'rin ko'p guruhga yangi talabalarni yozish kerak.",
                L.show("#view .gcard .bar", "Toʻlish", side="below"))
    await L.say("Guruhni ochamiz.", L.click("#view .gcard", "Guruhni ochamiz", side="right"))
    await L.wait_for("#view .journal")
    await L.say("Guruh sahifasi. Tepada: to'lish foizi, bo'sh o'rinlar, ustoz va shu oydagi darslar soni.",
                L.show("#view .stats", "Guruh haqida", side="below"))
    await L.say("Pastda — davomat jurnali: har bir talaba va har bir dars kuni. Katakdagi belgini shu yerda o'zgartirish mumkin.",
                L.show("#view .journal", "Davomat jurnali", side="above"))
    await L.say("Belgilar: bir — keldi, nol — sababli, X — besabab, chiziqcha — nofaol, nuqta — davomat olinmagan.",
                L.show("#view .card:has(.journal) .muted.small", "Belgilar", side="above"))
    await L.say("O'ng tomonda har bir talabaning qarzi. Boshqa oyni yuqoridagi ro'yxatdan tanlaysiz.",
                L.show("#view .card:has(.journal) select", "Oy", side="left"))
    await L.clear()
    await L.say("Endi yangi guruh ochamiz. Guruhlar ro'yxatiga qaytib, «Yangi guruh»ni bosamiz.",
                L.click("#view .back", "Orqaga", side="right", wait=1.2),
                L.click('[data-act="group-new"]', "Yangi guruh", side="below"))
    await L.wait_for(f("course", "select"))
    await L.say("Avval kurs.", L.choose(f("course", "select"), text="Backend", label="Kurs"))
    await L.say("Dars kunlari.", L.click(f("pattern", "button:nth-child(2)"), "Dars kunlari", side="below"))
    await L.say("Dars boshlanish vaqti. Tugash vaqti avtomatik ikki soat keyin qo'yiladi.",
                L.choose(f("new_start", "select"), "17:00", label="Boshlanish"))
    val = await option(L, '.overlay:last-child [data-f="teacher"] select')
    await L.say("Ustozni tanlaymiz.", L.choose(f("teacher", "select"), val, label="Ustoz"))
    await L.say("Yordamchi ustoz ixtiyoriy.", L.show('[data-f="supporter"]', "Yordamchi", side="above"))
    await L.say("Xonani tanlaymiz. Shu vaqtda band bo'lgan xona yonida «band!» deb yoziladi.",
                L.show('[data-f="room"]', "Xona", side="above", hold=0.6))
    val = await option(L, '.overlay:last-child [data-f="room"] select')
    await L.choose(f("room", "select"), val, label="Xona")
    if await L.exists('.overlay:last-child [data-f="warn"]:not([hidden])'):
        await L.say("Sariq ogohlantirish: shu vaqtda xona yoki ustoz boshqa guruhda band. Saqlash mumkin, lekin avval tekshiring.",
                    L.show('.overlay:last-child [data-f="warn"]', "Ogohlantirish", side="above"))
    await L.say("Boshlanish sanasi. Kelajakdagi sana qo'ysangiz, guruh «Rejada» bo'ladi va lidlarni unga sinov darsiga yozish mumkin.",
                L.show('[data-f="start"]', "Boshlanish", side="above"))
    await L.say("Guruh raqami avtomatik beriladi: kurs nomi va tartib raqami.",
                L.show('[data-f="num"]', "Guruh raqami", side="above"))
    await L.say("«Saqlash»ni bosamiz.", L.click(SAVE, "Saqlash", side="above"))
    await L.wait_for("#view .journal")
    await L.say("Guruh yaratildi va uning sahifasi ochildi. U bosh sahifadagi dars jadvalida ham darhol paydo bo'ladi.",
                L.show("#view .page-head", "Yangi guruh", side="below"))
    await L.say("Guruh ma'lumotlarini «Tahrirlash» tugmasi bilan o'zgartirasiz.",
                L.show('[data-act="group-edit"]', "Tahrirlash", side="below"))
    await L.clear()
    await L.say("Guruh ochishning tezroq yo'li — bosh sahifadagi jadval. Bosh sahifaga o'tamiz.",
                L.nav("dashboard", "Bosh sahifa"))
    await L.scroll(".sched", wait=1.0)
    # Birinchi xonaning ko'rinib turgan qismidan guruh bloki yo'q nuqtani topamiz
    spot = await L.js("""() => { const t = document.querySelector('.sched-track.addable'); if (!t) return null;
        const r = t.getBoundingClientRect(), y = r.top + r.height / 2, right = Math.min(r.right, innerWidth - 30);
        for (let x = r.left + 40; x < right; x += 12) { const e = document.elementFromPoint(x, y);
          if (e && (e === t || e.parentElement === t) && !e.closest('.sched-b')) return { x, y }; }
        return null; }""")
    await L.say("Jadvaldagi bo'sh joyni bosamiz — shu xona va vaqtga yangi guruh formasi ochiladi.",
                L.click_xy(spot, "Boʻsh joy"))
    await L.wait_for(f("course", "select"))
    await L.say("Xona, kun va vaqt allaqachon to'ldirilgan. Faqat kurs va ustozni tanlaysiz. Hozir bekor qilamiz.",
                L.show(MODAL + " .form", "Oldindan toʻldirilgan", side="right", hold=0.8))
    await L.click(MODAL + " .modal-foot [data-close]", "Bekor qilish", side="above")
    await L.say("Jadvaldagi guruh blokini bossangiz, boshqarish oynasi ochiladi: o'quvchi qo'shish, guruhdan chiqarish yoki guruhni yopish.",
                L.show(".sched-b:not(.plan)", "Guruhni boshqarish", side="below"))
    await L.say("Guruh tugasa, «Guruhni yopish» bilan oxirgi dars kunini belgilaysiz — guruh ertasidan nofaol bo'ladi.")
    await L.clear()
    await outro(L, "Qo'ng'iroqlar va SMS")
