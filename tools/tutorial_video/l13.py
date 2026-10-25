from common import SAVE, f, lesson, option, outro


@lesson("13", "ota_onalar_excel", "Ota-onalar bilan aloqa va Excel")
async def l13(L):
    await L.card("13-dars", "Ota-onalar bilan aloqa va Excel", "Suhbatlar jurnali va shartnomalarni faylga yuklash",
                 ["Kurs → guruh daraxti", "Qoʻngʻiroq va SMS havolalari", "Yangi yozuv qoʻshish",
                  "Izohni tahrirlash", "Shartnomalarni Excelga yuklash"],
                 text="O'n uchinchi darsda ota-onalar bilan aloqa jurnali va shartnomalarni Excel faylga yuklashni o'rganamiz.")
    await L.uncard()
    await L.nav("parentCalls", "Ota-onalar bilan aloqa")
    await L.say("Bu yerda ota-onalar bilan har bir suhbat yozib boriladi: talaba darsni qoldirsa, qarzi bo'lsa yoki muvaffaqiyati haqida.")
    await L.say("Chapda — kurslar va guruhlar daraxti, yonida yozuvlar soni. Guruhni bossangiz, faqat o'sha guruh yozuvlari qoladi.",
                L.show("#view .tree", "Daraxt", side="right"))
    await L.say("«Aloqa» ustunida talaba va vasiy telefonlari. Telefonda bossangiz — qo'ng'iroq yoki SMS ochiladi.",
                L.show("#view .tbl tbody tr:first-child td[data-label='Aloqa']", "Telefonlar", side="below"))
    await L.say("«Kim» ustunida yozuvni kim va qachon qo'shgani ko'rinadi.",
                L.show("#view .tbl tbody tr:first-child td[data-label='Kim']", "Kim yozdi", side="left"))
    await L.say("Yangi yozuv qo'shamiz.", L.click('[data-act="pcall-new"]', "Yangi yozuv", side="below"))
    await L.wait_for(f("course", "select"))
    val = await option(L, '.overlay:last-child [data-f="course"] select')
    await L.say("Kurs, keyin guruh, keyin talaba — har bir ro'yxat oldingisiga qarab qisqaradi.",
                L.choose(f("course", "select"), val, label="Kurs"))
    val = await option(L, '.overlay:last-child [data-f="group"] select')
    await L.choose(f("group", "select"), val, label="Guruh")
    val = await option(L, '.overlay:last-child [data-f="contract"] select')
    await L.choose(f("contract", "select"), val, label="Talaba")
    await L.say("Talabaning telefonlari chiqdi — qo'ng'iroq qilasiz.",
                L.show('.overlay:last-child [data-f="phones"]', "Telefonlar", side="below"))
    await L.say("Suhbatdan keyin nima deyilganini izohga yozasiz.",
                L.type(f("comment", "textarea"), "Otasi bilan gaplashdim: o'g'li uyda ham mashq qilyapti, to'lovni 15-sanagacha qiladi", "Izoh", delay=30, side="above"))
    await L.say("«Saqlash».", L.click(SAVE, "Saqlash", side="above"))
    await L.wait(1.2)
    await L.say("Yozuv jurnalga qo'shildi. Qalam belgisi bilan izohni tuzatish mumkin — tuzatgan odam va vaqt izoh ostida yoziladi.",
                L.show('#view [data-act="pcall-edit"]:not([disabled])', "Tahrirlash", side="left"))
    await L.clear()
    await L.say("Endi shartnomalarni Excel faylga yuklash. «Shartnoma yuklash» bo'limini ochamiz.",
                L.nav("export", "Shartnoma yuklash"))
    val = await option(L, "#ex-c", match="Backend") or await option(L, "#ex-c")
    await L.say("Kursni tanlaymiz.", L.choose("#ex-c", val, label="Kurs"))
    await L.say("Shu kursning guruhlari chiqdi, hammasi belgilangan. Keraksizini bosib, belgini olib tashlash mumkin.",
                L.show("#ex-g", "Guruhlar", side="below"))
    await L.say("«Excel'ga yuklash» tugmasini bosamiz.", L.click("#ex-go", "Excelga yuklash", side="right"))
    await L.wait(1.5)
    await L.keynote("shartnomalar.xlsx", "Talaba · telefonlar · vasiy · guruh · sanalar · status · toʻlangan · balans",
                    text="Fayl kompyuterga yuklandi. Unda har bir talaba: telefonlari, vasiysi, guruhi, sanalari, holati, to'lagan summasi va balansi.")
    await L.say("Shuningdek, Shartnomalar, To'lovlar va Qarzdorlar sahifalaridagi «Excel» tugmasi joriy filtr bo'yicha ro'yxatni yuklaydi.")
    await outro(L, "Sozlamalar")
