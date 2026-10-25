from common import MODAL, SAVE, f, lesson, outro


@lesson("11", "qongiroqlar_sms", "Qo'ng'iroqlar va SMS")
async def l11(L):
    await L.card("11-dars", "Qoʻngʻiroqlar va SMS", "Qabul telefonidagi qoʻngʻiroqlar va SMS jurnali",
                 ["Qoʻngʻiroqlar roʻyxati", "Javobsizlarga qayta qoʻngʻiroq", "Izoh yozish",
                  "Notanish raqamdan lid", "Statistika", "SMS qoliplari va jurnali"],
                 text="O'n birinchi darsda qo'ng'iroqlar bo'limini o'rganamiz. Qabul telefonidagi har bir qo'ng'iroq tugashi bilan shu yerga tushadi.")
    await L.uncard()
    await L.say("Qabul telefonida maxsus ilova o'rnatilgan. U qo'ng'iroqlarni tizimga yuboradi va SMS'larni jo'natadi. Suhbatning o'zi yozib olinmaydi.")
    await L.nav("calls", "Qoʻngʻiroqlar va SMS")
    await L.say("To'rtta tab: qo'ng'iroqlar, ularning statistikasi, SMS va SMS statistikasi.",
                L.show("#view .tabs", "Tablar", side="below"))
    await L.say("Ro'yxatda: yo'nalish va vaqt, raqam, kim ekani, lid ma'lumoti, suhbat davomiyligi, holat va izoh.",
                L.show("#view .tbl thead", "Ustunlar", side="below"))
    await L.say("Yo'nalish belgilari: kiruvchi — yashil, chiquvchi — ko'k, javobsiz — qizil.",
                L.show("#view .tbl tbody tr:first-child td:first-child", "Yoʻnalish", side="right"))
    await L.say("Raqam bazada bo'lsa, «Kim» ustunida talaba ismi chiqadi. Lid bo'lsa — uning statusi, kursi va manbasi.",
                L.show("#view .tbl tbody tr:first-child td[data-label='Kim']", "Kim", side="below"))
    await L.clear()
    await L.say("Eng muhimi — javobsiz qo'ng'iroqlar. Ular qizil qator bo'lib turadi. Filtrdan «Javobsiz — qayta qo'ng'iroq qilinmagan»ni tanlaymiz.",
                L.choose('select[data-filter="calls:dir"]', "missed_open", label="Javobsizlar"))
    await L.wait(1.5)
    if await L.exists('#view [data-act="call-cb"]'):
        await L.say("Bu raqamlarga qayta qo'ng'iroq qilish kerak. Qo'ng'iroq qilgach, «Qo'ng'iroq qilindi» tugmasini bosasiz.",
                    L.click('#view [data-act="call-cb"]', "Qoʻngʻiroq qilindi", side="left"))
        await L.wait(1.0)
    await L.say("Agar qabul telefonidan o'sha raqamga qo'ng'iroq qilsangiz, tizim buni o'zi belgilaydi.")
    await L.say("Filtrni «Barcha yo'nalishlar»ga qaytaramiz.",
                L.choose('select[data-filter="calls:dir"]', "", label="Barchasi"))
    await L.wait(1.2)
    await L.say("Har bir qo'ng'iroqqa izoh yozish mumkin. Qalam belgisini bosamiz.",
                L.click('#view [data-act="call-note"]', "Izoh", side="left"))
    await L.wait_for(f("comment", "textarea"))
    await L.say("Suhbat mazmunini qisqa yozamiz.", L.type(f("comment", "textarea"), "Flutter kursi narxini so'radi", "Izoh", delay=40))
    await L.click(SAVE, "Saqlash", side="above")
    await L.wait(1.0)
    await L.say("Noma'lum raqamdan qo'ng'iroq bo'lsa va u kursga qiziqsa — «Lid yaratish» tugmasini bosasiz.",
                L.choose('select[data-filter="calls:known"]', "0", label="Nomaʼlum raqamlar"))
    await L.wait(1.2)
    if await L.exists('#view [data-act="call-lead"]'):
        await L.click('#view [data-act="call-lead"]', "Lid yaratish", side="left")
        await L.wait_for(f("first_name"))
        await L.say("Lid formasi ochildi: telefon raqami allaqachon yozilgan, qo'ng'iroq vaqti esa izohga o'zi tushadi. Ism va qolganini to'ldirib saqlaysiz. Hozir bekor qilamiz.",
                    L.show('.overlay:last-child [data-f="first_name"]', "Ismini yozasiz", side="below", hold=0.6))
        await L.click(MODAL + " .modal-foot [data-close]", "Bekor qilish", side="above")
    await L.choose('select[data-filter="calls:known"]', "", label="Hamma raqamlar")
    await L.wait(1.0)
    await L.say("Lid bilan gaplashganingizdan keyin «Izoh yozish» tugmasi chiqadi — suhbat natijasini yozmaguningizcha bot eslatib turadi.")
    await L.clear()
    await L.say("«Statistika» tabi.", L.click('#view .tabs a[href*="tab=stats"]', "Statistika", side="below", wait=2.0))
    await L.say("Kartochkalar: jami qo'ng'iroqlar, kiruvchi, chiquvchi, javobsiz va ularga qayta qo'ng'iroq qilish uchun ketgan o'rtacha vaqt.",
                L.show("#view .stats", "Asosiy raqamlar", side="below"))
    await L.say("Pastda — qo'ng'iroq qilganlardan nechtasi lid bo'ldi va shartnoma tuzdi, soatlar bo'yicha diagramma va manbalar.",
                L.scroll(dy=600, wait=1.0), L.show("#view .grid-2", "Diagrammalar", side="above"))
    await L.clear()
    await L.say("«SMS» tabi.", L.scroll(dy=-3000, wait=0.6), L.click('#view .tabs a[href*="tab=sms"]:not([href*="smsstats"])', "SMS", side="below", wait=1.8))
    await L.say("Tepada — SMS qoliplari, ya'ni tayyor matnlar. Yangi qolip qo'shamiz.",
                L.click('[data-act="sms-tpl"]:not([data-id])', "Qolip qoʻshish", side="below"))
    await L.wait_for(f("text", "textarea"))
    await L.say("Nomi va matni. Matnda jingalak qavsdagi so'zlar o'rniga talaba ismi, oy, summa va muddat qo'yiladi.",
                L.type(f("name"), "Eslatma (qisqa)", "Nomi", delay=50))
    await L.say("Pastda nechta belgi va nechta SMS bo'lishi ko'rinadi. Qisqa matn arzonroq.",
                L.show('.overlay:last-child [data-f="count"]', "Belgilar soni", side="above"))
    await L.click(SAVE, "Saqlash", side="above")
    await L.wait(1.0)
    await L.say("Pastda — SMS jurnali: kimga, qaysi matn, holati va yetkazildimi. Ikki belgi — operator yetkazilganini tasdiqlagan.",
                L.scroll(dy=500, wait=1.0), L.show("#view .stats ~ .tbl-wrap", "SMS jurnali", side="above"))
    await L.say("Xato bo'lgan SMS'ni «Qayta yuborish» bilan, navbatdagini «Bekor qilish» bilan boshqarasiz. Mijozlardan kelgan SMS'lar ham shu yerda.")
    await L.clear()
    await L.say("«SMS statistikasi» — nechta SMS ketdi, yetkazildi va SMS'dan keyin nechta talaba to'lov qildi.",
                L.scroll(dy=-3000, wait=0.6), L.click('#view .tabs a[href*="smsstats"]', "SMS statistikasi", side="below", wait=1.8))
    await L.show("#view .stats", "SMS natijasi", side="below", hold=2.0)
    await L.clear()
    await outro(L, "Xarajatlar, o'tkazmalar va g'aznalar")
