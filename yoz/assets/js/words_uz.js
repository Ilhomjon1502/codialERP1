/* O'zbekcha so'zlar (lotin). Darslar faqat o'rganilgan harflardan iborat so'zlarni shu ro'yxatdan oladi.
   o' va g' oddiy apostrof (') bilan yoziladi — klaviaturada shu tugma bor. */
(function (Y) {
  'use strict';
  Y.WORDS_UZ = (
    // asosiy qator harflaridan (a s d f g h j k l)
    'dala sal kal lak aks asl fasl saf alda dalda jadal jasad faks kasal salla kalla kaskad falsafa hal hafsala ' +
    'shakl kashf hashak hakka galla ahd ahl jahl alla gala hassa kassa sadaf ' +
    // oila, uy, maktab
    'odam bola ota ona aka uka opa singil oila uy xona maktab sinf dars kitob daftar qalam ruchka sumka parta ' +
    'ustoz talaba do\'st mehmon qo\'shni ' +
    // kompyuter
    'kompyuter klaviatura sichqoncha ekran internet dastur fayl papka sayt tarmoq kod parol login tugma ' +
    'telefon rasm video musiqa o\'yin printer xotira disk ' +
    // til
    'so\'z gap harf raqam matn til o\'zbek ingliz rus savol javob ' +
    // joy
    'vatan shahar qishloq ko\'cha yo\'l bozor do\'kon bog\' hovli eshik deraza stol stul ' +
    // ovqat
    'non suv choy sut go\'sht osh palov olma nok uzum anor qovun tarvuz shaftoli gilos o\'rik behi sabzi piyoz ' +
    'kartoshka pomidor bodring karam guruch un tuz shakar asal yog\' tuxum qand ovqat nonushta tushlik ' +
    // vaqt va tabiat
    'kun tun kecha bugun ertaga hafta oy yil soat daqiqa vaqt bahor yoz kuz qish quyosh osmon bulut yomg\'ir ' +
    'qor shamol havo issiq sovuq iliq daryo ko\'l dengiz tog\' tosh qum yer o\'rmon daraxt gul barg o\'t maysa ' +
    // hayvonlar
    'mushuk it ot sigir qo\'y echki tovuq xo\'roz qush baliq ari kapalak sher bo\'ri tulki quyon ayiq fil ' +
    'maymun ilon toshbaqa ' +
    // sifatlar
    'qizil sariq yashil ko\'k oq qora pushti katta kichik uzun qisqa baland past tez sekin yangi eski yaxshi ' +
    'yomon chiroyli aqlli kuchli zo\'r oson qiyin to\'g\'ri xato ' +
    // sonlar
    'bir ikki uch to\'rt besh olti yetti sakkiz to\'qqiz o\'n yuz ming ' +
    // olmosh va yordamchi so'zlar
    'men sen u biz siz ular bu shu o\'sha nima kim qachon qayer qanday nega ha yo\'q va bilan uchun lekin ham ' +
    'endi hozir doim ko\'p oz hamma har birga ' +
    // muomala
    'salom rahmat iltimos xayr ' +
    // fe'llar
    'keldi ketdi bordi yozdi o\'qidi ko\'rdi aytdi berdi oldi qildi yozish o\'qish o\'rganish bilish ishlash ' +
    'o\'ynash yugurish yurish sakrash suzish kulish uxlash ichish ' +
    // kasblar va qadriyatlar
    'shifokor haydovchi dasturchi muhandis quruvchi oshpaz sotuvchi rassom sport futbol to\'p g\'alaba maqsad ' +
    'orzu bilim ilm aql sabr mehnat baxt quvonch tinchlik sevgi hurmat odob bayroq'
  ).split(/\s+/).filter((w) => w && /^[a-z']+$/.test(w));
})(window.Y = window.Y || {});
