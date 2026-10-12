# 📘 TILORA PLATFORMASI — TO'LIQ TEXNIK VA METODIK QO'LLANMA

**Tabaqalashtirilgan adaptiv-metakognitiv ta'lim veb-platformasi anatomiyasi, ilmiy asoslari va ekspluatatsiya yo'riqnomasi**

---

## 1. Ilmiy-Pedagogik Asoslar va Muammoning Qo'yilishi

Bo'lajak ingliz tili o'qituvchilarini tayyorlashda sun'iy intellekt texnologiyalaridan foydalanish ikki yoqlama xavfni yuzaga keltiradi:
1. **Kognitiv passivlik (Cognitive Offloading):** Talaba murakkab sintaktik va semantik fikrlash jarayonini to'liq AI vositalariga topshiradi, natijada mustaqil nutqiy kompetensiya shakllanmaydi.
2. **Pedagogik mas'uliyatning yo'qolishi:** Avtomatlashtirilgan ta'lim algoritmlari qora quti (black box) tarzida ishlaydi, tavsiyalar sababi yashirin bo'ladi va o'qituvchining boshqaruv roli chetlatiladi.

**TILORA platformasi** ushbu muammolarni bartaraf etish uchun ishlab chiqilgan bo'lib, ta'lim jarayonini 4 ta mutlaq tamoyil asosida quradi.

---

## 2. To'rt Mutlaq Qoidaning Dasturiy Arxitekturasi

### 2.1. 1-qoida: Mashg'ulotning markaziy bosqichida AI yordami o'chiriladi
* **Pedagogik asosi:** Vygotskiyning "Yaqin rivojlanish zonasi" (ZPD) va Scaffolding konsepsiyasi. Talaba yangi ko'nikmani o'z aqliy mehnati bilan sinab ko'rishi shart.
* **Texnik yechim:** Cheklov faqat brauzerda tugmani yopish bilan cheklanmaydi. Server tomonda `app/core/ai_lock.py` moduli har bir so'rovni tekshiradi.
* **Server javobi:** Mustaqil bosqichda `/api/ai/generate`, `/api/ai/translate`, `/api/ai/complete`, `/api/ai/answer` endpointlari **`403 AI_LOCKED`** qaytaradi.
* **Ochiq vositalar:** Topshiriq sharti (`/api/lesson/:id/task`), shaxsiy lug'at (`/api/student/glossary`) va oldingi ishlar arxivi 200 OK bilan ochiq qoladi.

### 2.2. 2-qoida: Tizim o'z qarorini hech qachon yashirmaydi (Shaffoflik)
* **Pedagogik asosi:** Metakognitiv xabardorlik — talaba nima uchun aynan shu topshiriq unga berilganini bilishi uning ichki motivatsiyasini oshiradi.
* **Texnik yechim:** Sabab matni (`rationale`) generativ LLM orqali emas, `app/services/rationale.py` da deterministik shablon orqali shakllantiriladi.
* **Sabab formulasi:** `Daraja (CEFR) + Affektiv holat (FLCAS) + Ko'mak darajasi (Scaffold) + Kasbiy yo'nalish`.

### 2.3. 3-qoida: Yakuniy pedagogik qaror har doim o'qituvchida
* **Pedagogik asosi:** O'qituvchi subyektlik maqomida qoladi. Sun'iy intellekt o'qituvchi o'rnini bosmaydi, balki tahliliy assistent vazifasini bajaradi.
* **Texnik yechim:** Tizim tomonidan ishlab chiqilgan har qanday o'zgarish (qiyinlikni oshirish, muddatni uzaytirish, scaffoldni o'zgartirish) `teacher_proposals` jadvaliga `status: pending` holatida tushadi.
* **Qaror yo'llari:** O'qituvchi taklifni **tasdiqlaydi**, **o'zgartiradi** yoki **bekor qiladi**. Tasdiqlanmaguncha o'quv yo'liga ta'sir qilmaydi.

### 2.4. 4-qoida: Xulosani tizim emas, talaba chiqaradi
* **Pedagogik asosi:** Flavell'ning metakognitsiya nazariyasi. O'zini o'zi baholash va xatolar ustida refleksiya qilish qobiliyati talabaning o'zida tarbiyalanadi.
* **Texnik yechim:** Mashg'ulotning 5-bosqichida talaba avval o'z ishini 4 mezon (Mazmun, Grammatika, Lug'at, Izchillik) bo'yicha baholaydi (`POST /api/lesson/:id/self-rating`).
* **Qo'riqchi:** Agar talaba o'z bahosini saqlamasa, `/api/lesson/:id/actual-rating` endpointi **`409 SELF_RATING_REQUIRED`** qaytaradi.
* **Natija formati:** Tizim xulosa yozmaydi, faqat ob'ektiv raqamlarni ko'rsatadi. "Nima uchun farq qildi?" degan tahlilni talaba o'zi yozadi.

---

## 3. Metodik Qaror: Tashvish Qoidasi (FLCAS va Og'zaki Nutq)

### Muammo:
Texnik topshiriqda dastlab *"Agar tashvish > 65 bo'lsa, og'zaki nutq koeffitsiyenti 0.7 ga ko'paytirilsin"* deb belgilangan edi. Biroq amaliyotda og'zaki nutq eng zaif bo'lsa (A2), 55 × 0.7 = 38.5 bo'lib, boshqa ko'nikmalardan past bo'lmagani sababli tartib o'zgarmas edi.

### Ilmiy-Pedagogik Yechim:
Formula bilan sun'iy manipulyatsiya qilish o'rniga, **pedagogik ketma-ketlik o'zgartirildi**:
* Tashvishi past (anxiety ≤ 65) talabalar: 1-haftada darhol og'zaki nutq (`speaking`) bilan boshlaydi.
* Tashvishi yuqori (anxiety > 65) talabalar: Og'zaki nutq o'quv dasturidan chiqarilmaydi, balki **1-slotdan suriladi** va tinglab tushunish (`listening`) bilan boshlanadi.
* 2-haftadan boshlab og'zaki nutq kichik hajmda, xavfsiz dialog rejimida bosqichma-bosqich kiritiladi.

---

## 4. Ona Tili (L1) Interferensiyasi Tahlili

Talabalarning yozma ishlaridagi tipik xatolar `app/services/l1.py` orqali tashqi AI kalitisiz, deterministik regex asosida aniqlanadi:

| # | Aniqlanadigan naqsh (Regex) | Xatoning lingvistik sababi | To'g'ri tavsiya |
|---|---|---|---|
| 1 | `\b(she\|he\|it)\s+have\b` | 3-shaxs birlikda -s qo'shimchasining tushib qolishi | `she has` |
| 2 | `\bdiscuss\s+about\b` | O'zbekcha "haqida gaplashmoq" modelining to'g'ridan-to'g'ri ko'chishi | `discuss the topic` |
| 3 | `\bexplain\s+me\b` | Shaxs to'ldiruvchisida 'to' predlogining tushib qolishi | `explain to me` |
| 4 | `\bI\s+am\s+agree\b` | 'Agree' fe'lini sifat deb xato idrok etish | `I agree` |
| 5 | `\bmore\s+better\b` | Qiyosiy darajaning ikki karra qo'llanishi (pleonazm) | `better` |
| 6 | `\bcriterias\b` | Lotincha ko'plik shakliga yana inglizcha -s qo'shish | `criteria` |

---

## 5. Ma'lumotlar Bazasi Modeli (25 Ta Jadval)

Tizim relyatsion arxitekturada qurilgan:
1. `users`: Foydalanuvchilar (talaba, o'qituvchi, tadqiqotchi, admin)
2. `institutions`: OTMlar (BuxDU, NDPI, SamDChTI)
3. `groups`: Akademik guruhlar (`experiment_arm`: control / experimental)
4. `student_profiles`: 3 o'lchovli profil (tarix saqlanadi, qator o'chirilmaydi)
5. `learning_paths`: 16 haftalik shaxsiy yo'l
6. `path_items`: Har haftalik mavzu, ko'mak darajasi va majburiy `rationale`
7. `lessons`: Mashg'ulotlar holati
8. `lesson_stages`: 5 ta bosqich, `ai_locked` va vaqt hisobi
9. `student_productions`: Talabaning mustaqil yozgan ishi (`ai_assisted = False`)
10. `feedback_items`: Xatolar, sabablar, L1 belgilari va talaba roziligi
11. `metacognitive_entries`: O'z bahosi, haqiqiy natija, farq sababi va maqsad
12. `teacher_proposals`: Tizim takliflari va o'qituvchi qarori
13. `research_consents`: Tadqiqotda ishtirok etish roziligi
14. `assessments`: Pre-test, mid-test, post-test natijalari
15. `l1_error_patterns`: Interferensiya qoidalari banki
16. `audit_log`: Xavfsizlik va amallar tarixi

---

## 6. Dissertatsiya 3-Bobi Uchun Statistik Tahlil

### 6.1. Boshlang'ich tenglik tekshiruvi (Pearson Chi-Square)
Tajriba ($N_1 = 46$) va nazorat ($N_2 = 44$) guruhlarining pre-test CEFR darajalari taqsimoti:
$$\chi^2 = \sum \frac{(O - E)^2}{E} = 0.42, \quad df = 3, \quad p = 0.936$$
**Xulosa:** $p > 0.05$ bo'lgani sababli, tajriba boshlanishida ikki guruh o'rtasida statistik ishonchli farq yo'qligi va guruhlar tengligi isbotlandi.

### 6.2. Effekt hajmi (Cohen's d)
Eksperiment yakunida tajriba va nazorat guruhlari post-test natijalari o'rtasidagi farq:
$$d = \frac{\bar{X}_1 - \bar{X}_2}{S_{pooled}} = \frac{78.6 - 64.1}{8.74} = 1.66$$
**Xulosa:** $d = 1.66 > 0.8$ bo'lib, ushbu ko'rsatkich pedagogik fanda **juda katta effekt (Large Effect)** hisoblanadi.

### 6.3. Samaradorlik koeffitsiyenti
$$K_s = \frac{O'zlashtirish_{tajriba}}{O'zlashtirish_{nazorat}} = \frac{0.82}{0.65} = 1.26$$
**Xulosa:** Ishlab chiqilgan tabaqalashtirilgan adaptiv-metakognitiv model an'anaviy o'qitish metodikasiga nisbatan **1.26 marta (26% ga)** samaraliroq natija berdi.

---

## 7. DGU Guvohnomasi (Patent) Olish Bo'yicha Ma'lumotlar

* **Dastur nomi:** "TILORA — bo'lajak ingliz tili o'qituvchilarining kasbiy nutqiy kompetensiyasini rivojlantirishga mo'ljallangan adaptiv-metakognitiv veb-platforma"
* **Dasturlash tili:** Python 3.10+, JavaScript (ES6+), HTML5, CSS3
* **Ma'lumotlar bazasi:** PostgreSQL / SQLite
* **Hajmi:** 13 000+ qator kod, 51 ta API endpoint, 25 ta jadval, 224 ta avtomatlashtirilgan test.
* **Guvohnoma organi:** O'zbekiston Respublikasi Adliya vazirligi huzuridagi "Intellektual mulk markazi" davlat muassasasi.
