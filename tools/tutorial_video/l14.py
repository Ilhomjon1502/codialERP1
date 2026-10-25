from common import MODAL, SAVE, f, lesson, outro


def tab(key):
    return f'#view .settings .side-tabs a[href$="tab={key}"]'


@lesson("14", "sozlamalar", "Sozlamalar")
async def l14(L):
    await L.card("14-dars", "Sozlamalar", "Kurslar, narxlar, xonalar va boshqa maʼlumotnomalar",
                 ["Kurslar va kurs narxlari", "Oydagi dars soni", "Chegirma va xarajat turlari",
                  "Lid manbalari", "Xonalar va dars kunlari", "Foydalanuvchilar va ruxsatlar"],
                 text="Oxirgi, o'n to'rtinchi darsda sozlamalarni ko'rib chiqamiz. Bu yerda tizimning barcha ma'lumotnomalari saqlanadi.")
    await L.uncard()
    await L.say("Diqqat: sozlamalardagi o'zgarish butun tizimga ta'sir qiladi. Har bir o'zgarishni rahbar bilan kelishib qiling.")
    await L.nav("settings", "Sozlamalar")
    await L.say("Chapda — bo'limlar ro'yxati. Birinchisi — «Kurslar»: kurs nomi, amaldagi narxi va holati.",
                L.show("#view .settings .side-tabs", "Boʻlimlar", side="right", hold=0.8),
                L.show("#view .settings-body .tbl", "Kurslar", side="left"))
    await L.say("«Kurs narxlari» — har bir kursning oylik narxi va o'zgarish tarixi.",
                L.click(tab("prices"), "Kurs narxlari", side="right", wait=1.0))
    await L.say("Narx o'zgarsa, eski narx o'chirilmaydi: yangi narx qaysi oydan amal qilishi bilan qo'shiladi. Shu oydan boshlab qarzlar yangi narxda hisoblanadi.",
                L.show("#view .price-row", "Narx tarixi", side="below"))
    await L.say("«Oydagi dars soni» — juda muhim. Har oy birinchi kuni tizim kalendardan har bir dars jadvali uchun darslar sonini hisoblab «Taklif» qiladi.",
                L.click(tab("freq"), "Oydagi dars soni", side="right", wait=1.0))
    await L.say("Bayram kunlari bo'lsa, qalam belgisi bilan sonni kamaytirasiz. Rahbar tasdiqlagach, shu oy uchun qarz va ustoz haqi hisoblanadi.",
                L.show("#view .settings-body .tbl", "Darslar soni", side="above"))
    await L.say("Bir dars narxi — oylik narx shu songa bo'linadi. Shuning uchun bu son har oy to'g'ri bo'lishi kerak.")
    await L.say("«Chegirma turlari» — har bir chegirmaning eng ko'p miqdori. To'lovda bundan ortiq chegirma kiritib bo'lmaydi.",
                L.click(tab("discounts"), "Chegirma turlari", side="right", wait=1.0))
    await L.say("«Xarajat kategoriyalari» — xarajat turlari va ularni kim kirita olishi.",
                L.click(tab("expcats"), "Xarajat kategoriyalari", side="right", wait=1.0))
    await L.say("«Lid manbalari» — lid qayerdan kelgani. Yangi reklama boshlansa, yangi manba qo'shamiz.",
                L.click(tab("sources"), "Lid manbalari", side="right", wait=1.0))
    await L.say("«Qo'shish»ni bosamiz.", L.click('#view [data-act="crud-add"]', "Qoʻshish", side="below"))
    await L.wait_for(f("name"))
    await L.say("Nomini yozamiz va holati — «Faol».", L.type(f("name"), "TikTok", "Nomi", delay=80))
    await L.click(SAVE, "Saqlash", side="above")
    await L.wait(1.0)
    await L.say("Yangi manba qo'shildi va endi lid formasida chiqadi. Reklama to'xtasa, manbani «Nofaol» qilasiz — eski lidlar statistikasi saqlanib qoladi.",
                L.show('#view .settings-body tr:has-text("TikTok")', "Yangi manba", side="below"))
    await L.say("«Xonalar» — xona nomi va sig'imi. Guruhning to'lishi shu sig'imdan hisoblanadi.",
                L.click(tab("rooms"), "Xonalar", side="right", wait=1.0))
    await L.say("«Dars kunlari» — haftaning qaysi kunlari dars bo'lishi, masalan dushanba, chorshanba, juma.",
                L.click(tab("patterns"), "Dars kunlari", side="right", wait=1.0))
    await L.say("«G'aznalar» va «Filiallar»ni faqat rahbariyat o'zgartiradi, siz ko'rasiz.",
                L.click(tab("accounts"), "Gʻaznalar", side="right", wait=1.0))
    await L.say("«Foydalanuvchilar» — barcha xodimlar: lavozimi, filiali, telefoni va holati. Yangi xodimni Bosh menejer qo'shadi.",
                L.click(tab("users"), "Foydalanuvchilar", side="right", wait=1.2))
    await L.say("«Rollar va ruxsatlar» — har bir lavozim qaysi bo'limda nima qila olishi. Harflar: ko'rish, qo'shish, tahrirlash, o'chirish va tasdiqlash.",
                L.click(tab("roles"), "Rollar va ruxsatlar", side="right", wait=1.5))
    await L.say("Pastda — tahrirlash muddatlari. Masalan, siz to'lov va xarajatni faqat shu kuni, shartnomani yetti kun ichida tuzata olasiz.",
                L.scroll("#view .settings-body h3", wait=1.0), L.show("#view .settings-body h3 + .tbl-wrap", "Muddatlar", side="above"))
    await L.clear()
    await L.card("Codial ERP · yoʻriqnoma", "Barcha darslar tugadi",
                 "Savol boʻlsa — Bosh menejerga yoki Topshiriqlar orqali yozing",
                 ["Har suhbatdan keyin izoh", "Qayta bogʻlanish vaqtini qoʻying", "Toʻlovda chekni bering",
                  "Kelmaganlar bilan bogʻlaning", "Kassani har kuni solishtiring", "Telegram botni ulang"],
                 text="Tabriklaymiz, barcha darslar tugadi! Eng muhimlari: har suhbatdan keyin izoh yozing, qayta bog'lanish vaqtini qo'ying, to'lovda chek bering, kelmaganlar bilan bog'laning va kassani har kuni solishtiring. Ishingizga omad!",
                 hold=2.0)
