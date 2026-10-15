/**
 * TILORA Platformasi — DSc Dissertatsiyasi Qo'shimchalari Moduli
 * 
 * Muallif: Ikramova Aziza Aminovna
 * Mavzu: Ingliz tilini sun'iy intellekt texnologiyalari asosida o'qitish metodikasini takomillashtirish
 * 
 * Modul quyidagilarni o'z ichiga oladi:
 * 1. 3 tilli interfeys (O'zbek / English / Русский)
 * 2. Dissertatsiya 4-bobi uchun to'liq statistik modullar va Word/Excel eksport
 * 3. To'rt nutqiy ko'nikma (Listening, Reading, Speaking, Writing) interaktiv tizimi
 * 4. Sun'iy intellekt kelib chiqishi nishoni (AI-Origin Badge / Shaffoflik)
 * 5. Cheklangan internet tezligi va tejamkor oflayn rejim
 * 6. Tadqiqotda ishtirok etish va akademik halollik roziligi (Research Consent)
 */

(function() {
  'use strict';

  // ==========================================
  // 1. UCH TILLI INTERFEYS (i18n) LUG'ATI
  // ==========================================
  const I18N_DICT = {
    uz: {
      brand_tagline: "Adaptiv-metakognitiv ta'lim veb-platformasi",
      page_title: "TILORA Platformasi",
      page_subtitle: "Buxoro davlat universiteti · Chet tillar fakulteti",
      nav_student_room: "Talaba Xonasi",
      nav_profile: "Uch o'lchovli profil",
      nav_path: "16 haftalik yo'l",
      nav_lesson: "Mashg'ulot (5 bosqich)",
      nav_diagnostic: "Diagnostika va anketa",
      nav_materials: "O'quv fanlari & Testlar",
      nav_teacher_room: "O'qituvchi & Boshqaruv",
      nav_teacher_proposals: "Takliflar va nazorat",
      nav_subjects: "Fanlar & Sillabus (AI)",
      nav_diag_manage: "Diagnostika & Anketa savollari",
      nav_research_room: "Ilmiy Tadqiqot",
      nav_research: "Tadqiqotchi statistikasi",
      nav_admin_room: "Tizim",
      nav_admin: "Administrator paneli",
      principles_title: "To'rt tamoyil:",
      principle_1: "1. Mustaqil bosqichda AI yopiq",
      principle_2: "2. Sabab shablonda ochiq",
      principle_3: "3. Yakuniy qaror o'qituvchida",
      principle_4: "4. Xulosani talaba chiqaradi",
      btn_consent: "Etika & Rozilik",
      login_btn: "Profilga kirish",
      logout_btn: "Chiqish",
      wifi_btn: "Wi-Fi",
      prof_banner_title: "Obuna Holati:",
      prof_card_cefr: "1. Til ko'nikmalari (CEFR)",
      prof_card_esp: "2. Kasbiy yo'nalish",
      prof_card_cog: "3. Kognitiv-affektiv profil",
      path_main_heading: "16 haftalik shaxsiylashtirilgan o'quv yo'li",
      diag_main_heading: "Diagnostika va Kognitiv Anketa",
      teacher_main_heading: "O'qituvchi boshqaruv paneli",
      admin_main_heading: "Super Administrator Boshqaruv Paneli",
      dm_main_title: "🎧 Diagnostika testi va Anketa savollari",
      dm_main_desc: "Talabalar \"Diagnostika va anketa\" bo'limida ko'radigan savollarni o'zingiz yuklang: yozma yoki audio (tinglab tushunish) savollar, JSON import va FLCAS anketasi.",
      dm_why_title: "Qanday ishlaydi?",
      dm_why_body: "Savollar <b>umumiy</b> (barcha fanlar uchun) yoki <b>muayyan fanga</b> biriktirilgan bo'lishi mumkin. Talaba diagnostika ekranida fanni tanlaganda shu fanning savollari + umumiy savollar chiqadi. Bank bo'sh bo'lsa, standart 8 ta test va 12 ta anketa savoli ko'rsatiladi. Super admin barcha o'qituvchilarning fanlariga savol qo'sha oladi.",
      dm_select_subject_label: "📚 Qaysi fan uchun savollar ko'rsatilsin / qo'shilsin?",
      dm_sec_diag_title: "1. Diagnostika testi savollari (CEFR 4 ko'nikma)",
      btn_new_question: "➕ Yangi savol",
      btn_json_import: "📥 JSON import",
      btn_copy_defaults: "📋 Standartni nusxalash",
      btn_export: "⬇ Eksport",
      btn_delete_all: "🗑 Hammasini o'chirish",
      dm_form_new_diag: "Yangi diagnostika savoli",
      dm_form_skill_label: "Ko'nikma",
      dm_form_cefr_label: "CEFR darajasi",
      dm_form_q_label: "Savol matni / ko'rsatma *",
      dm_form_opts_label: "Javob variantlari * (to'g'risini belgilang)",
      dm_form_add_opt: "+ Variant qo'shish",
      dm_form_rationale_label: "Izoh (nima uchun shu javob to'g'ri)",
      dm_form_audio_toggle: "🎧 Bu savolga audio biriktiriladi",
      dm_form_audio_ai: "🤖 Matn yozaman — AI ovozga aylantiradi",
      dm_form_audio_file: "📁 Tayyor audio fayl yuklayman",
      dm_form_audio_text_label: "Talaba tinglaydigan matn — AI ovozga aylantiradi",
      dm_form_tts_btn: "🔊 Tinglab ko'rish",
      btn_cancel: "Bekor qilish",
      btn_save: "💾 Saqlash",
      dm_sec_survey_title: "2. Kognitiv-affektiv anketa (FLCAS) savollari",
      dm_survey_desc: "Har bir savol 1–5 Likert shkalasida baholanadi. O'lcham profildagi qaysi ko'rsatkichga ta'sir qilishini belgilaydi: xavotir (FLCAS), yuklama sig'imi, sur'at, avtonomiya, motivatsiya.",
      dm_form_new_survey: "Yangi anketa savoli",
      dm_survey_dim_label: "O'lcham (profilga ta'siri)",
      dm_survey_weight_label: "Vazn (0.1–3.0)",
      dm_survey_prompt_uz_label: "Savol (o'zbekcha) *",
      dm_survey_prompt_en_label: "Savol (inglizcha, ixtiyoriy)",
      low_bandwidth_on: "⚡ Tejamkor rejim: YOQIK",
      low_bandwidth_off: "⚡ Tejamkor rejim",
      offline_notice: "⚠️ Internet aloqasi cheklangan: Tizim hududiy kesh (oflayn) rejimida ishlamoqda.",
      ai_origin_badge: "🤖 Sun'iy intellekt tomonidan hosil qilingan material • Model: TAAM-AI • Shaffoflik: 100%",
      stage_1: "1-bosqich: Dars maqsadi va yo'nalishi",
      stage_2: "2-bosqich: Leksik va tarkibiy ko'mak (Scaffold)",
      stage_3: "3-bosqich: Mustaqil nutqiy mahsulot (AI yopiq)",
      stage_4: "4-bosqich: Tahlil va L1 interferensiyasi",
      stage_5: "5-bosqich: Metakognitiv refleksiya",
      skill_writing: "✍️ Yozma nutq (Writing)",
      skill_speaking: "🎙️ Og'zaki nutq (Speaking)",
      skill_listening: "🎧 Tinglab tushunish (Listening)",
      skill_reading: "📖 O'qish (Reading)",
      btn_start_record: "🎙️ Ovoz yozishni boshlash",
      btn_stop_record: "⏹️ To'xtatish va saqlash",
      btn_eval_speaking: "🤖 Og'zaki nutqni AI tahlil qilish",
      btn_play_audio: "▶️ Audioni tinglash",
      btn_pause_audio: "⏸️ To'xtatish",
      consent_title: "Tadqiqotda ishtirok etish va Akademik halollik deklaratsiyasi",
      consent_accept: "Roziman va qabul qilaman",
      research_title: "DSc Dissertatsiyasi 4-bobi: Matematik-statistik tahlil moduli",
      research_sub: "Ikramova Aziza Aminovna — «Ingliz tilini sun'iy intellekt texnologiyalari asosida o'qitish metodikasini takomillashtirish»",
      btn_export_word: "📥 Dissertatsiya jadvallari (.docx)",
      btn_export_excel: "📊 To'liq statistika (.xlsx)",
      btn_export_csv: "📄 CSV eksport",
      tab_4_2: "4.2-jadval. Talabalar soni",
      tab_4_4: "4.4-jadval. Boshlang'ich tenglik",
      tab_4_5: "4.5-jadval. Guruh dinamikasi",
      tab_4_6: "4.6-jadval. Nutqiy ko'nikmalar",
      tab_4_7: "4.7-jadval. Metakognitsiya",
      tab_4_8: "4.8-jadval. Bespalko K",
      tab_4_9: "4.9-jadval. Umumiy xulosa",
      prof_banner_free_desc: "PRO tarif bilan cheksiz AI testlar, taqdimotlar va to'liq tahlildan foydalaning.",
      prof_banner_pro_desc: "Barcha AI vositalari, testlar, taqdimotlar va to'liq tahlildan cheksiz foydalanishingiz mumkin.",
      prof_btn_upgrade: "👑 PRO ga o'tish (To'lov)",
      prof_btn_active: "👑 PRO Faol",
      prof_cefr_desc: "CEFR darajasi umumlashtirilmaydi, har ko'nikma alohida dinamikada o'lchanadi.",
      prof_esp_subtitle: "Integratsiyalashgan kasbiy modullar:",
      prof_esp_modules: "• Dars kuzatuvi va tahlili metodikasi<br>• Pedagogik diskurs va ko'rsatmalar berish<br>• Baholash rubrikalari va kriteriyalar",
      prof_esp_footer: "Tilni o'rganish bilan birga uni o'rgatish metodikasi uyg'unlashtiriladi.",
      prof_cog_load: "Material hajmi sig'imi",
      prof_cog_pace: "Bajarish sur'ati",
      prof_cog_anxiety: "Chet tili tashvishi (FLCAS)",
      prof_cog_autonomy: "Mustaqil ishlash tayyorgarligi",
      prof_cog_footer: "Haqiqiy xulq-atvor orqali o'lchanadi. VARK kabi asossiz testlar kiritilmagan.",
      skill_listening_label: "Tinglab tushunish",
      skill_reading_label: "O'qish",
      skill_speaking_label: "Og'zaki nutq",
      skill_writing_label: "Yozma nutq",
      path_subtitle: "Hozirda 4-hafta davom etmoqda · Qatorni bosing — mavzuning mashg'ulot sahifasi ochiladi",
      path_chip_approved: "O'qituvchi tomonidan tasdiqlangan",
      path_scaffolding_why: "<b>Ko'mak darajasi qanday pasaytiriladi (Scaffolding Dinamikasi)</b><br>Talaba mustaqil bajarish bosqichini ketma-ket 3 mashg'ulotda muvaffaqiyatli topshirsa, ko'mak darajasi bir pog'ona pasaytiriladi: <i>to'liq ko'mak → qisman ko'mak → ko'maksiz (avtonom)</i>. Har bir o'zgarish o'qituvchi tasdig'i orqali amalga oshadi.",
      lesson_back_path: "← 16 haftalik o'quv yo'liga qaytish",
      lesson_skill_label: "Nutqiy faoliyat turi:",
      lesson_stage_1: "1. Kirish",
      lesson_stage_2: "2. Tayyorgarlik",
      lesson_stage_3: "3. Mustaqil bajarish (AI Qulflangan)",
      lesson_stage_4: "4. Tahlil va izohlar",
      lesson_stage_5: "5. Refleksiya",
      btn_finish_prod: "Ishni yakunlash va tahlil bosqichiga o'tish →",
      ai_lock_title: "1-QOIDA: Sun'iy intellekt yordami yopiq",
      ai_lock_desc: "Bu bosqichda tizim tayyor javob bermaydi. Ko'nikma talaba o'z aqliy mehnati bilan matn yaratgandagina shakllanadi.",
      btn_lock_gen: "Matn generatsiyasi",
      btn_lock_trans: "Tarjima",
      btn_lock_cont: "Davomini yozish",
      btn_lock_ans: "Tayyor javob",
      allowed_tools_title: "Foydalanish ruxsat etilgan vositalar",
      btn_review_prompt: "Topshiriq shartini qayta o'qish",
      btn_glossary: "O'z lug'atingiz (Glossary)",
      btn_archive: "Oldingi ishlaringiz arxivi",
      diag_subtitle: "CEFR bo'yicha 4 ta nutqiy ko'nikma va FLCAS tashvish profilini aniqlash",
      diag_subj_label: "📚 Fan bo'yicha diagnostika:",
      diag_subj_hint: "Fan tanlansa, shu fanga tegishli ko'nikmalar va savollar chiqadi.",
      diag_skills_label: "🎯 Fan ko'nikmalari:",
      diag_sec1_title: "1. Diagnostika Testi (CEFR 4 Ko'nikma)",
      diag_sec2_title: "2. Kognitiv-Affektiv Anketa (FLCAS Shkalasi)",
      diag_sec2_desc: "Quyidagi tasdiqlarga qanchalik qo'shilishingizni 1 dan 5 gacha baholang (1 - Mutlaqo qo'shilmayman, 5 - To'liq qo'shilaman):",
      btn_submit_diag: "📤 Diagnostika va anketa natijalarini yuborish (Profilni yangilash) →",
      sm_title: "📚 Mustaqil topshiriqlar",
      sm_desc: "Avval fanni tanlang, so'ng o'qituvchi yuklagan testlarni ishlang, prezentatsiyalarni o'rganing va yozma mashg'ulotni topshiring",
      btn_refresh: "Yangilash",
      sm_select_subject_label: "📖 O'quv fanini tanlang:",
      sm_opt_all_subjects: "📂 Fanlar ro'yxati (fanni tanlang)",
      sm_search_label: "🔍 Mavzu yoki nom bo'yicha qidirish:",
      sm_search_placeholder: "Masalan: Morfologiya, CEFR, Test...",
      sm_tab_all: "Barchasi",
      sm_tab_test: "📝 Testlar",
      sm_tab_presentation: "🖥️ Slaydlar",
      sm_tab_writing: "✍️ Yozma mashg'ulot",
      sm_tab_plan: "📄 Dars rejalari",
      prof_why_box: "<b>2-Qoida Asosi: Nima uchun profil va o'quv yo'li aynan shunday shakllantirildi?</b><br>Talabaning og'zaki nutq ko'rsatkichi eng zaif (A2), chet tili tashvishi esa yuqori (71/100). Shu bois 1-haftada og'zaki nutq topshirig'i kiritilmasdan, tinglab tushunishga o'tkazildi. Og'zaki nutq mashqlari esa kichik hajmda, dialog formatida va xatoga erkin yo'l qo'yiladigan xavfsiz muhitda 2-haftadan boshlab asta-sekin joriy etiladi.",
      prof_anx_high: "Yuqori",
      prof_anx_med: "O'rtacha",
      prof_anx_low: "Past",
      path_scaffold_none: "ko'mak yo'q",
      path_scaffold_partial: "qisman ko'mak",
      path_scaffold_full: "to'liq ko'mak",
      path_status_done: " · ✅ yakunlangan",
      path_status_active: " · ▶ hozirgi",
      path_action_lesson: "Mashg'ulot →",
      path_week_suffix: "-hafta",
      path_weeks_label: "hafta",
      lesson_timer_rem: "Qolgan vaqt:",
      lesson_stage1_title: "1-bosqich: Dars maqsadi va yo'nalishi",
      lesson_stage1_next: "Tayyorgarlik bosqichiga o'tish →",
      lesson_stage2_title: "2-bosqich: Leksik va tarkibiy ko'mak (Scaffold)",
      lesson_stage2_desc: "Mustaqil yozishdan oldin quyidagi akademik birikmalar bilan tanishib chiqing:",
      lesson_stage2_sample: "Namuna tuzilma",
      lesson_stage2_sample_body: "1. Kirish: Yozma nutqni baholashdagi asosiy muammo.<br>2. Asosiy qism: 2-3 ta muhim mezon tahlili.<br>3. Xulosa: O'qituvchining xolis baholashdagi mas'uliyati.",
      lesson_stage2_next: "Mustaqil bajarishga o'tish (AI qulflanadi) →",
      lesson_stage2_ai_title: "DeepSeek AI Yordamchisi (2-bosqich)",
      lesson_stage2_ai_desc: "Mustaqil yozishdan oldin akademik tuzilma yoki yo'naltiruvchi namuna so'rang.",
      lesson_stage2_ai_btn: "Namuna / Reja so'rash ✨",
      lesson_stage3_task_title: "Mustaqil topshiriq",
      lesson_stage3_editor_placeholder: "Matnni faqat o'zingiz yozing. Ushbu bosqichda sun'iy intellekt vositalari o'chirilgan...",
      lesson_stage3_auto_save: "Matn avtomatik saqlanmoqda",
      lesson_stage3_chars: "ta harf",
      lesson_stage3_words: "ta so'z",
      lesson_stage3_lines: "ta qator",
      lesson_stage4_title: "4-bosqich: Matn tahlili va sababli izohlar",
      lesson_stage4_desc: "Tizim tayyor tuzatish bermaydi, faqat xato sababini ko'rsatadi. Har bir izohga munosabatingizni bildiring.",
      lesson_stage4_why: "<b>Tizim izoh berish qoidasi</b><br>Izohlar Hattie & Timperley modeli bo'yicha berildi. Ona tili interferensiyasi (o'zbek tilidagi sintaksisning ingliz tiliga xato ko'chirilishi) alohida belgilandi. Yakuniy tuzatish qarori talabada qoladi.",
      lesson_stage4_ai_deep: "DeepSeek AI bilan chuqur lingvistik tahlil",
      lesson_stage4_next: "Refleksiyaga o'tish →",
      lesson_stage5_step1_title: "1-qadam · O'z bahoyingiz (Metakognitiv baholash)",
      lesson_stage5_step1_desc: "Avval o'zingiz halol baholang. AI bahosi faqat shundan keyin ochiladi va u sizning bahoyingizga ta'sir qilmaydi.",
      crit_content: "Mazmun to'liqligi",
      crit_grammar: "Grammatik aniqlik",
      crit_lexis: "Lug'aviy boylik",
      crit_coherence: "Izchillik va bog'liqlik",
      lesson_stage5_rule4_hint: "To'rttala mezon baholangach, AI bahosi yonma-yon solishtirish uchun ochiladi (4-qoida).",
      lesson_stage5_step2_title: "2-qadam · AI bahosi va solishtirish",
      lesson_stage5_step2_desc: "Sun'iy intellekt sizning matningizni 4 mezon bo'yicha mustaqil baholaydi va har bir bahoning sababini ko'rsatadi.",
      lesson_stage5_locked_ai: "🔒 <b>AI bahosi qulflangan</b><br>O'z baholashingizni qo'yishingiz bilan AI bahosi yonma-yon ochiladi.",
      lesson_stage5_th_crit: "Mezon",
      lesson_stage5_th_you: "Siz",
      lesson_stage5_th_ai: "AI",
      lesson_stage5_th_diff: "Farq",
      lesson_stage5_gap_title: "Farq sababini o'z so'zlaringiz bilan tushuntiring:",
      lesson_stage5_gap_ph: "Nima uchun o'z bahoyingiz haqiqiy natijadan farq qildi?",
      lesson_stage5_goal_title: "Keyingi mashg'ulot uchun shaxsiy maqsadingiz:",
      lesson_stage5_goal_ph: "Masalan: Keyingi safar ona tili ta'siridagi xatolarni qayta tahrir qilaman",
      lesson_stage5_btn_finish: "Mashg'ulotni yakunlash",
      lesson_stage5_why: "<b>4-Qoida: Avval o'z bahoyingiz, keyin AI bahosi.</b><br>AI sizning ishingizni mustaqil baholaydi va sababini ko'rsatadi, lekin sizning o'z bahoyingizni to'ldirib bermaydi. Ikki baho orasidagi farqni ko'rib, xulosani o'zingiz yozasiz. O'zini o'zi boshqarish va refleksiya ko'nikmasi shu tarzda shakllanadi.",
      diag_likert_1: "Mutlaqo qo'shilmayman",
      diag_likert_2: "Qisman qo'shilmayman",
      diag_likert_3: "Neytral",
      diag_likert_4: "Qo'shilaman",
      diag_likert_5: "To'liq qo'shilaman",
      diag_btn_play_audio: "Audioni tinglash",
      diag_btn_stop_audio: "To'xtatish",
      diag_audio_instruction: "🎧 Matnni eshitib, to'g'ri variantni belgilang",
      diag_audio_playing: "Ijro etilmoqda...",
      diag_q_label: "Savol",
      diag_survey_label: "Anketa",
      diag_all_skills: "📋 Barchasi",
      sm_card_view: "Ko'rish",
      sm_card_download: "Yuklab olish",
      sm_card_read_plan: "Rejani o'qish",
      sm_card_take_test: "Testni topshirish",
      sm_card_retake_test: "Qayta ishlash",
      sm_card_start_writing: "Yozishni boshlash",
      sm_card_rewrite: "Qayta yozish",
      sm_card_open_tasks: "Topshiriqlarni ochish →",
      sm_card_status_completed: "bajarilgan",
      sm_card_status_viewed: "👁️ Ko'rilgan",
      sm_card_status_pending: "⏳ Bajarilmagan",
      sm_card_subject_label: "Fan",
      sm_card_topic_label: "Mavzu",
      sm_type_test: "Nazorat Testi",
      sm_type_presentation: "Taqdimot (Slaydlar)",
      sm_type_writing: "Yozma mashg'ulot",
      sm_type_plan: "Dars rejasi",
      sm_empty_subjects: "📂 Sizning guruhingiz uchun hali fan ochilmagan.",
      sm_empty_materials_title: "Hech qanday o'quv materiali topilmadi",
      sm_empty_materials_search: "Qidiruv bo'yicha mos material yo'q.",
      sm_empty_materials_none: "O'qituvchi hali bu fan bo'yicha test yoki slaydlar yaratmagan.",
      sm_unit_materials: "ta material",
      sm_unit_topics: "ta mavzu",
      sm_done_label: "Bajarilgan",
      st_test_modal_title: "Test sinovi",
      st_test_modal_desc: "Mavzu bo'yicha interaktiv bilimni tekshirish",
      st_test_modal_count_label: "Savollar:",
      btn_exit: "Chiqish",
      st_test_submit_btn: "✅ Testni yakunlash va natijani tekshirish",
      st_slide_modal_title: "Prezentatsiya",
      st_slide_img_loading: "🎨 Rasm tayyorlanmoqda...",
      st_slide_speaker_notes_label: "🎙️ O'qituvchi eslatmasi (Speaker Notes):",
      st_slide_prompt_label: "🖼️ Rasm generatsiya prompti (Midjourney/DALL-E uchun):",
      st_slide_download_btn: "📥 Slaydni yuklab olish (HTML/PDF)",
      st_slide_copy_btn: "📋 Matnni nusxalash",
      st_slide_prev_btn: "← Oldingi",
      st_slide_next_btn: "Keyingi →",
      st_writing_modal_title: "Yozma topshiriq",
      st_writing_rubric_summary: "📏 Baholash mezonlari (4 mezon × 5 ball)",
      st_writing_editor_label: "✍️ Matningiz",
      st_writing_self_rating_title: "🪞 O'z-o'zini baholash (1–5): topshirishdan oldin o'zingizga baho bering",
      st_writing_submit_btn: "📤 Topshirish va AI baho olish",
      st_plan_modal_title: "Dars Rejasi (Lesson Plan)",
      st_plan_modal_desc: "Mavzu bo'yicha dars ishlanmasi",
      st_plan_copy_btn: "📋 Rejani nusxalash",
      btn_close: "Yopish",
      nav_proposals: "Takliflar va fikr-mulohazalar",
      prop_page_title: "💡 Takliflar va Pedagogik Muloqot Markazi",
      prop_page_desc: "O'qituvchilar va talabalar o'rtasida taklif almashish, AI tavsiyalari va pedagogik qarorlar (3-Qoida)",
      btn_send_proposal: "Yangi taklif yuborish",
      prop_tab_all: "Barchasi",
      prop_tab_inbox: "Menga kelgan",
      prop_tab_sent: "Men yuborgan",
      prop_tab_system: "Tizim (AI)",
      prop_filter_direction: "Yo'nalish:",
      prop_filter_status: "Holat:",
      prop_modal_title: "Yangi taklif yuborish",
      prop_modal_desc: "O'qituvchilar va talabalar bilan fikr almashish, metodik yoki o'quv taklifi kiritish",
      prop_rec_type_label: "👥 Kimga yuborilsin? (Qabul qiluvchi toifasi):",
      prop_rec_person_label: "👤 Qabul qiluvchini tanlang:",
      prop_direction_label: "🔄 Taklif yo'nalishi:",
      prop_cat_label: "🏷️ Taklif sohasi / Toifasi:",
      prop_title_label: "📝 Taklif mavzusi (Qisqa va aniq) *:",
      prop_text_label: "💬 Taklifning to'liq matni va mazmuni *:",
      prop_basis_label: "🎯 Taklif asosi yoki kutilayotgan natijasi:",
      btn_submit_proposal: "Taklifni yuborish",
      prop_decision_title: "Taklif bo'yicha qaror",
      prop_decision_desc: "Qaroringizga pedagogik izoh yoki tavsiya qo'shishingiz mumkin",
      prop_decision_comment_label: "✍️ Izoh / Pedagogik sharh (ixtiyoriy):",
      nav_dev_api: "Dasturchi va API",
      nav_api_docs: "API Hujjatlari (Docs)",
      btn_api_docs: "API Docs",
      api_docs_title: "⚡ TILORA RESTful API & OpenAPI Hujjatlari",
      api_docs_subtitle: "117 ta endpoint · JWT xavfsizligi · 4 ta pedagogik tamoyil · DSc ilmiy tahlil · Swagger UI & ReDoc integratsiyasi",
      api_tab_catalog: "Endpointlar Katalogi",
      api_tab_tester: "Jonli API Tester (Console)",
      api_tab_arch: "Arxitektura va 4 Tamoyil",
      api_tab_swagger: "O'rnatilgan Swagger UI",
      api_tab_keys: "API Kalitlari (Keys)",
      api_keys_sec_title: "🔑 Dasturiy Integratsiya API Kalitlari (API Keys)",
      api_keys_sec_desc: "Dasturchilar (Developer) va Super Administrator (Admin) uchun tashqi tizimlar, mobil ilovalar va skriptlar bilan ulanish kalitlari",
      btn_create_api_key: "Yangi API Kalit yaratish",
      api_stat_total_keys: "Jami API Kalitlar",
      api_stat_active_keys: "Faol Kalitlar",
      api_stat_revoked_keys: "Bekor qilingan / Muddati o'tgan",
      api_keys_table_title: "Mavjud API Kalitlari",
      api_keys_guide_title: "API Kalitidan qanday foydalaniladi?",
      modal_api_key_title: "Yangi API Kalit Yaratish",
      modal_api_key_desc: "Tashqi tizimlar, mobil ilovalar va integratsiya uchun xavfsiz kalit",
      modal_api_key_name_label: "📝 Kalit nomi (Nima maqsadda ishlatiladi?) *:"
    },
    en: {
      brand_tagline: "Adaptive-Metacognitive Educational Web Platform",
      page_title: "TILORA Platform",
      page_subtitle: "Bukhara State University · Faculty of Foreign Languages",
      nav_student_room: "Student Cabinet",
      nav_profile: "Three-Dimensional Profile",
      nav_path: "16-Week Learning Path",
      nav_lesson: "Lesson (5 Stages)",
      nav_diagnostic: "Diagnostic & Survey",
      nav_materials: "Subjects & Tests",
      nav_teacher_room: "Teacher & Management",
      nav_teacher_proposals: "Proposals & Control",
      nav_subjects: "Curriculum & Syllabus (AI)",
      nav_diag_manage: "Diagnostic Questions Bank",
      nav_research_room: "Scientific Research",
      nav_research: "Researcher Analytics",
      nav_admin_room: "System",
      nav_admin: "Administrator Panel",
      principles_title: "Four Principles:",
      principle_1: "1. AI is locked during independent stage",
      principle_2: "2. Rationale is explicit in template",
      principle_3: "3. Final decision rests with teacher",
      principle_4: "4. Conclusions formulated by student",
      btn_consent: "Ethics & Consent",
      login_btn: "Sign In",
      logout_btn: "Sign Out",
      wifi_btn: "Wi-Fi",
      prof_banner_title: "Subscription Status:",
      prof_card_cefr: "1. Language Skills (CEFR)",
      prof_card_esp: "2. Professional Field (ESP)",
      prof_card_cog: "3. Cognitive-Affective Profile",
      path_main_heading: "16-Week Personalized Learning Path",
      diag_main_heading: "Diagnostic & Cognitive Survey",
      teacher_main_heading: "Teacher Management Panel",
      admin_main_heading: "Super Administrator Management Panel",
      dm_main_title: "🎧 Diagnostic Test & Survey Question Bank",
      dm_main_desc: "Manage the questions seen by students in the \"Diagnostic & Survey\" section: written or audio (listening) items, JSON import, and FLCAS inventory.",
      dm_why_title: "How it works",
      dm_why_body: "Questions can be <b>general</b> (applicable to all courses) or linked to a <b>specific course</b>. When a student chooses a course on the diagnostic screen, course-specific + general questions appear. If the question bank is empty, the default 8 test and 12 survey items are displayed. Super administrators can manage questions for all courses.",
      dm_select_subject_label: "📚 Select course to view or add questions:",
      dm_sec_diag_title: "1. Diagnostic Test Questions (CEFR 4 Skills)",
      btn_new_question: "➕ New Question",
      btn_json_import: "📥 JSON Import",
      btn_copy_defaults: "📋 Copy Defaults",
      btn_export: "⬇ Export",
      btn_delete_all: "🗑 Delete All",
      dm_form_new_diag: "New Diagnostic Question",
      dm_form_skill_label: "Skill",
      dm_form_cefr_label: "CEFR Level",
      dm_form_q_label: "Question Text / Prompt *",
      dm_form_opts_label: "Answer Options * (select correct answer)",
      dm_form_add_opt: "+ Add Option",
      dm_form_rationale_label: "Rationale (explanation of correct answer)",
      dm_form_audio_toggle: "🎧 Attach audio to this question",
      dm_form_audio_ai: "🤖 Type text — AI generates speech",
      dm_form_audio_file: "📁 Upload ready audio file",
      dm_form_audio_text_label: "Listening passage — AI voice synthesis",
      dm_form_tts_btn: "🔊 Preview Audio",
      btn_cancel: "Cancel",
      btn_save: "💾 Save",
      dm_sec_survey_title: "2. Cognitive-Affective Survey (FLCAS) Questions",
      dm_survey_desc: "Each question is evaluated on a 1–5 Likert scale. Dimension determines impact on profile: anxiety (FLCAS), cognitive load capacity, pace, autonomy, motivation.",
      dm_form_new_survey: "New Survey Question",
      dm_survey_dim_label: "Dimension (Profile Impact)",
      dm_survey_weight_label: "Weight (0.1–3.0)",
      dm_survey_prompt_uz_label: "Question (Uzbek) *",
      dm_survey_prompt_en_label: "Question (English, optional)",
      low_bandwidth_on: "⚡ Low-Bandwidth: ON",
      low_bandwidth_off: "⚡ Low-Bandwidth",
      offline_notice: "⚠️ Limited Internet Connectivity: Operating in local offline cache mode.",
      ai_origin_badge: "🤖 AI-Generated Material • Model: TAAM-AI • Transparency: 100%",
      stage_1: "Stage 1: Lesson Goals & Orientation",
      stage_2: "Stage 2: Lexical & Structural Scaffolding",
      stage_3: "Stage 3: Independent Production (AI-Locked)",
      stage_4: "Stage 4: Feedback & L1 Interference",
      stage_5: "Stage 5: Metacognitive Reflection",
      skill_writing: "✍️ Writing Practice",
      skill_speaking: "🎙️ Speaking Practice",
      skill_listening: "🎧 Listening Practice",
      skill_reading: "📖 Reading Practice",
      btn_start_record: "🎙️ Start Voice Recording",
      btn_stop_record: "⏹️ Stop and Save",
      btn_eval_speaking: "🤖 Analyze Speech with AI",
      btn_play_audio: "▶️ Play Audio",
      btn_pause_audio: "⏸️ Pause Audio",
      consent_title: "Informed Research Consent & Academic Integrity Declaration",
      consent_accept: "I Agree & Accept",
      research_title: "DSc Dissertation Chapter IV: Mathematical-Statistical Analysis Module",
      research_sub: "Aziza Aminovna Ikramova — «Improving the Methodology of Teaching English Based on AI Technologies»",
      btn_export_word: "📥 Dissertation Tables (.docx)",
      btn_export_excel: "📊 Full Statistics (.xlsx)",
      btn_export_csv: "📄 CSV Export",
      tab_4_2: "Table 4.2. Sample Distribution",
      tab_4_4: "Table 4.4. Baseline Equivalence",
      tab_4_5: "Table 4.5. Within-Group Growth",
      tab_4_6: "Table 4.6. Speech Skills",
      tab_4_7: "Table 4.7. Metacognition",
      tab_4_8: "Table 4.8. Bespalko K",
      tab_4_9: "Table 4.9. Synthesis & Conclusions",
      prof_banner_free_desc: "Unlock unlimited AI tests, presentations, and comprehensive analytics with PRO tier.",
      prof_banner_pro_desc: "You have unlimited access to all AI tools, tests, presentations, and analytics.",
      prof_btn_upgrade: "👑 Upgrade to PRO",
      prof_btn_active: "👑 PRO Active",
      prof_cefr_desc: "CEFR levels are not generalized; each skill is measured individually.",
      prof_esp_subtitle: "Integrated Professional Modules:",
      prof_esp_modules: "• Lesson observation and analysis methodology<br>• Pedagogical discourse and teacher instructions<br>• Assessment rubrics and criteria",
      prof_esp_footer: "Language acquisition is integrated with language teaching methodology.",
      prof_cog_load: "Cognitive Load Capacity",
      prof_cog_pace: "Learning Pace",
      prof_cog_anxiety: "Foreign Language Anxiety (FLCAS)",
      prof_cog_autonomy: "Autonomy Readiness",
      prof_cog_footer: "Measured through objective behavioral data. Unfounded models like VARK are excluded.",
      skill_listening_label: "Listening",
      skill_reading_label: "Reading",
      skill_speaking_label: "Speaking",
      skill_writing_label: "Writing",
      path_subtitle: "Currently on Week 4 · Click a row to open the lesson page",
      path_chip_approved: "Approved by instructor",
      path_scaffolding_why: "<b>Scaffolding Fading Dynamics</b><br>When a student successfully completes the independent production stage across 3 consecutive lessons, the support level fades by one step: <i>full support → partial support → autonomous (no support)</i>. Each transition requires teacher approval.",
      lesson_back_path: "← Back to 16-week learning path",
      lesson_skill_label: "Speech Activity Type:",
      lesson_stage_1: "1. Introduction",
      lesson_stage_2: "2. Preparation",
      lesson_stage_3: "3. Independent Work (AI Locked)",
      lesson_stage_4: "4. Analysis & Feedback",
      lesson_stage_5: "5. Reflection",
      btn_finish_prod: "Finish work and proceed to analysis →",
      ai_lock_title: "RULE 1: AI Assistance Locked",
      ai_lock_desc: "The system provides no pre-made answers at this stage. Competence develops only when learners produce language through their own cognitive effort.",
      btn_lock_gen: "Text Generation",
      btn_lock_trans: "Translation",
      btn_lock_cont: "Continue Writing",
      btn_lock_ans: "Complete Answer",
      allowed_tools_title: "Permitted Tools",
      btn_review_prompt: "Re-read task prompt",
      btn_glossary: "Personal Glossary",
      btn_archive: "Previous Submissions Archive",
      diag_subtitle: "Assessment of 4 CEFR speech skills and FLCAS anxiety profile",
      diag_subj_label: "📚 Course Diagnostic:",
      diag_subj_hint: "Selecting a course shows its specific skills and questions.",
      diag_skills_label: "🎯 Course Skills:",
      diag_sec1_title: "1. Diagnostic Test (CEFR 4 Skills)",
      diag_sec2_title: "2. Cognitive-Affective Survey (FLCAS Scale)",
      diag_sec2_desc: "Rate your level of agreement with each statement from 1 to 5 (1 - Strongly disagree, 5 - Strongly agree):",
      btn_submit_diag: "📤 Submit Diagnostic & Survey Results (Update Profile) →",
      sm_title: "📚 Self-Study Tasks",
      sm_desc: "First select a course, then take tests, study slides, and submit writing tasks assigned by the instructor",
      btn_refresh: "Refresh",
      sm_select_subject_label: "📖 Select Course:",
      sm_opt_all_subjects: "📂 Course list (select course)",
      sm_search_label: "🔍 Search by topic or title:",
      sm_search_placeholder: "E.g., Morphology, CEFR, Test...",
      sm_tab_all: "All",
      sm_tab_test: "📝 Tests",
      sm_tab_presentation: "🖥️ Slides",
      sm_tab_writing: "✍️ Writing Tasks",
      sm_tab_plan: "📄 Lesson Plans",
      prof_why_box: "<b>Rule 2 Rationale: Why was the profile and learning path designed this way?</b><br>The student's speaking proficiency is at A2 level, with high foreign language anxiety (71/100). Therefore, oral tasks are postponed from week 1 in favor of listening comprehension. Speaking practice is introduced gradually from week 2 in low-stakes dialogic tasks.",
      prof_anx_high: "High",
      prof_anx_med: "Moderate",
      prof_anx_low: "Low",
      path_scaffold_none: "no support",
      path_scaffold_partial: "partial support",
      path_scaffold_full: "full support",
      path_status_done: " · ✅ completed",
      path_status_active: " · ▶ current",
      path_action_lesson: "Lesson →",
      path_week_suffix: "",
      path_weeks_label: "Weeks",
      lesson_timer_rem: "Time remaining:",
      lesson_stage1_title: "Stage 1: Lesson Goals & Orientation",
      lesson_stage1_next: "Proceed to Preparation →",
      lesson_stage2_title: "Stage 2: Lexical & Structural Scaffolding",
      lesson_stage2_desc: "Familiarize yourself with the following academic collocations before independent writing:",
      lesson_stage2_sample: "Sample Structure",
      lesson_stage2_sample_body: "1. Introduction: Core challenges in language assessment.<br>2. Body: Analysis of 2–3 key criteria.<br>3. Conclusion: Teacher's ethical responsibility in objective evaluation.",
      lesson_stage2_next: "Proceed to Independent Work (AI Locked) →",
      lesson_stage2_ai_title: "DeepSeek AI Assistant (Stage 2)",
      lesson_stage2_ai_desc: "Request an academic structure or guiding sample before independent work.",
      lesson_stage2_ai_btn: "Request Sample / Outline ✨",
      lesson_stage3_task_title: "Independent Task",
      lesson_stage3_editor_placeholder: "Write your response independently. AI assistance is disabled during this stage...",
      lesson_stage3_auto_save: "Text is auto-saved",
      lesson_stage3_chars: "characters",
      lesson_stage3_words: "words",
      lesson_stage3_lines: "lines",
      lesson_stage4_title: "Stage 4: Text Analysis & Rationalized Feedback",
      lesson_stage4_desc: "The system does not provide ready-made corrections, but highlights error causes. Reflect on each feedback item.",
      lesson_stage4_why: "<b>Feedback Policy</b><br>Feedback is structured according to the Hattie & Timperley model. L1 interference (syntax transfer from native language) is explicitly tagged. Final revision decisions remain with the student.",
      lesson_stage4_ai_deep: "In-depth Linguistic Analysis with DeepSeek AI",
      lesson_stage4_next: "Proceed to Reflection →",
      lesson_stage5_step1_title: "Step 1 · Self-Assessment (Metacognitive Evaluation)",
      lesson_stage5_step1_desc: "Evaluate your own work honestly first. AI evaluation is revealed only after and does not influence your self-score.",
      crit_content: "Content Completeness",
      crit_grammar: "Grammatical Accuracy",
      crit_lexis: "Lexical Resource",
      crit_coherence: "Coherence & Cohesion",
      lesson_stage5_rule4_hint: "Once all four criteria are evaluated, the AI evaluation is unlocked for side-by-side comparison (Rule 4).",
      lesson_stage5_step2_title: "Step 2 · AI Evaluation & Comparison",
      lesson_stage5_step2_desc: "Artificial intelligence independently assesses your text across 4 criteria and explains the rationale for each score.",
      lesson_stage5_locked_ai: "🔒 <b>AI evaluation is locked</b><br>Submit your self-assessment to unlock AI ratings side-by-side.",
      lesson_stage5_th_crit: "Criterion",
      lesson_stage5_th_you: "You",
      lesson_stage5_th_ai: "AI",
      lesson_stage5_th_diff: "Diff",
      lesson_stage5_gap_title: "Explain the discrepancy in your own words:",
      lesson_stage5_gap_ph: "Why did your self-rating differ from the AI score?",
      lesson_stage5_goal_title: "Personal goal for the next lesson:",
      lesson_stage5_goal_ph: "E.g., Next time I will proofread for L1 interference and syntactic errors",
      lesson_stage5_btn_finish: "Complete Lesson",
      lesson_stage5_why: "<b>Rule 4: Self-Assessment First, AI Evaluation Second.</b><br>The AI independently evaluates your work and provides rationales, but never fills out your self-evaluation. By examining the gap between ratings, you articulate your own metacognitive conclusions. Self-regulation and reflective thinking develop through this deliberate process.",
      diag_likert_1: "Strongly disagree",
      diag_likert_2: "Disagree",
      diag_likert_3: "Neutral",
      diag_likert_4: "Agree",
      diag_likert_5: "Strongly agree",
      diag_btn_play_audio: "Play Audio",
      diag_btn_stop_audio: "Stop Audio",
      diag_audio_instruction: "🎧 Listen to the passage and select the correct option",
      diag_audio_playing: "Playing...",
      diag_q_label: "Question",
      diag_survey_label: "Survey",
      diag_all_skills: "📋 All",
      sm_card_view: "View",
      sm_card_download: "Download",
      sm_card_read_plan: "Read Plan",
      sm_card_take_test: "Take Test",
      sm_card_retake_test: "Retake",
      sm_card_start_writing: "Start Writing",
      sm_card_rewrite: "Rewrite",
      sm_card_open_tasks: "Open Tasks →",
      sm_card_status_completed: "completed",
      sm_card_status_viewed: "👁️ Viewed",
      sm_card_status_pending: "⏳ Pending",
      sm_card_subject_label: "Course",
      sm_card_topic_label: "Topic",
      sm_type_test: "Assessment Test",
      sm_type_presentation: "Presentation (Slides)",
      sm_type_writing: "Writing Task",
      sm_type_plan: "Lesson Plan",
      sm_empty_subjects: "📂 No courses available for your group yet.",
      sm_empty_materials_title: "No learning materials found",
      sm_empty_materials_search: "No materials match your search query.",
      sm_empty_materials_none: "The instructor has not created tests or slides for this course yet.",
      sm_unit_materials: "materials",
      sm_unit_topics: "topics",
      sm_done_label: "Completed",
      st_test_modal_title: "Assessment Test",
      st_test_modal_desc: "Interactive knowledge assessment on the topic",
      st_test_modal_count_label: "Questions:",
      btn_exit: "Exit",
      st_test_submit_btn: "✅ Submit Test & Check Score",
      st_slide_modal_title: "Presentation",
      st_slide_img_loading: "🎨 Preparing visual...",
      st_slide_speaker_notes_label: "🎙️ Speaker Notes:",
      st_slide_prompt_label: "🖼️ Image Generation Prompt (Midjourney/DALL-E):",
      st_slide_download_btn: "📥 Download Slides (HTML/PDF)",
      st_slide_copy_btn: "📋 Copy Presentation Text",
      st_slide_prev_btn: "← Previous",
      st_slide_next_btn: "Next →",
      st_writing_modal_title: "Writing Assignment",
      st_writing_rubric_summary: "📏 Assessment Rubrics (4 criteria × 5 points)",
      st_writing_editor_label: "✍️ Your Writing",
      st_writing_self_rating_title: "🪞 Metacognitive Self-Assessment (1–5): evaluate yourself before submitting",
      st_writing_submit_btn: "📤 Submit & Receive AI Evaluation",
      st_plan_modal_title: "Lesson Plan",
      st_plan_modal_desc: "Structured lesson plan on the topic",
      st_plan_copy_btn: "📋 Copy Lesson Plan",
      btn_close: "Close",
      nav_proposals: "Proposals & Feedback",
      prop_page_title: "💡 Proposals & Pedagogical Control Center",
      prop_page_desc: "Exchange proposals between teachers and students, AI recommendations, and pedagogical decisions (Rule 3)",
      btn_send_proposal: "Send New Proposal",
      prop_tab_all: "All",
      prop_tab_inbox: "Inbox",
      prop_tab_sent: "Sent",
      prop_tab_system: "System (AI)",
      prop_filter_direction: "Direction:",
      prop_filter_status: "Status:",
      prop_modal_title: "Send New Proposal",
      prop_modal_desc: "Exchange ideas with teachers and students, propose methodological or learning enhancements",
      prop_rec_type_label: "👥 Recipient Category:",
      prop_rec_person_label: "👤 Select Recipient:",
      prop_direction_label: "🔄 Proposal Direction:",
      prop_cat_label: "🏷️ Proposal Category:",
      prop_title_label: "📝 Proposal Subject (Short & clear) *:",
      prop_text_label: "💬 Full Proposal Content *:",
      prop_basis_label: "🎯 Rationale / Expected Outcome:",
      btn_submit_proposal: "Submit Proposal",
      prop_decision_title: "Proposal Decision",
      prop_decision_desc: "You can add a pedagogical note or comment to your decision",
      prop_decision_comment_label: "✍️ Comment / Pedagogical note (optional):",
      nav_dev_api: "Developer & API",
      nav_api_docs: "API Documentation",
      btn_api_docs: "API Docs",
      api_docs_title: "⚡ TILORA RESTful API & OpenAPI Documentation",
      api_docs_subtitle: "117 endpoints · JWT Security · 4 Pedagogical Principles · DSc Research Analytics · Swagger UI & ReDoc Integration",
      api_tab_catalog: "Endpoints Catalog",
      api_tab_tester: "Live API Tester (Console)",
      api_tab_arch: "Architecture & 4 Principles",
      api_tab_swagger: "Embedded Swagger UI",
      api_tab_keys: "API Keys & Tokens",
      api_keys_sec_title: "🔑 Software Integration API Keys",
      api_keys_sec_desc: "API Keys for Developers and Super Administrator to integrate external systems, mobile apps, and scripts",
      btn_create_api_key: "Generate New API Key",
      api_stat_total_keys: "Total API Keys",
      api_stat_active_keys: "Active Keys",
      api_stat_revoked_keys: "Revoked / Expired Keys",
      api_keys_table_title: "Existing API Keys",
      api_keys_guide_title: "How to authenticate using API Key?",
      modal_api_key_title: "Create New API Key",
      modal_api_key_desc: "Secure API key for third-party systems, mobile applications, and automation",
      modal_api_key_name_label: "📝 Key Name (Purpose of usage) *:"
    },
    ru: {
      brand_tagline: "Адаптивно-метакогнитивная образовательная веб-платформа",
      page_title: "Платформа TILORA",
      page_subtitle: "Бухарский государственный университет · Факультет иностранных языков",
      nav_student_room: "Кабинет студента",
      nav_profile: "Трёхмерный профиль",
      nav_path: "16-недельная траектория",
      nav_lesson: "Занятие (5 этапов)",
      nav_diagnostic: "Диагностика и анкета",
      nav_materials: "Учебные предметы и тесты",
      nav_teacher_room: "Преподаватель и контроль",
      nav_teacher_proposals: "Предложения и контроль",
      nav_subjects: "Предметы и силлабус (ИИ)",
      nav_diag_manage: "Вопросы диагностики и анкеты",
      nav_research_room: "Научные исследования",
      nav_research: "Статистика исследователя",
      nav_admin_room: "Система",
      nav_admin: "Панель администратора",
      principles_title: "Четыре принципа:",
      principle_1: "1. ИИ закрыт на этапе самостоятельной работы",
      principle_2: "2. Причина открыта в шаблоне",
      principle_3: "3. Окончательное решение за преподавателем",
      principle_4: "4. Выводы делает студент",
      btn_consent: "Этика и согласие",
      login_btn: "Войти в профиль",
      logout_btn: "Выход",
      wifi_btn: "Wi-Fi",
      prof_banner_title: "Статус подписки:",
      prof_card_cefr: "1. Языковые навыки (CEFR)",
      prof_card_esp: "2. Профессиональное направление (ESP)",
      prof_card_cog: "3. Когнитивно-аффективный профиль",
      path_main_heading: "16-недельная индивидуальная траектория обучения",
      diag_main_heading: "Диагностика и когнитивная анкета",
      teacher_main_heading: "Панель управления преподавателя",
      admin_main_heading: "Панель супер-администратора",
      dm_main_title: "🎧 Банк вопросов диагностики и анкеты",
      dm_main_desc: "Управляйте вопросами для раздела «Диагностика и анкета»: текстовые или аудио-вопросы (аудирование), импорт JSON и шкала FLCAS.",
      dm_why_title: "Как это работает?",
      dm_why_body: "Вопросы могут быть <b>общими</b> (для всех предметов) или привязанными к <b>конкретному предмету</b>. При выборе предмета на экране диагностики отображаются предметные + общие вопросы. Если банк пуст, показываются стандартные 8 тестовых и 12 анкетных вопросов. Администраторы могут добавлять вопросы ко всем предметам.",
      dm_select_subject_label: "📚 Для какого предмета отображать / добавлять вопросы?",
      dm_sec_diag_title: "1. Вопросы диагностического теста (4 навыка CEFR)",
      btn_new_question: "➕ Новый вопрос",
      btn_json_import: "📥 Импорт JSON",
      btn_copy_defaults: "📋 Скопировать стандарт",
      btn_export: "⬇ Экспорт",
      btn_delete_all: "🗑 Удалить всё",
      dm_form_new_diag: "Новый диагностический вопрос",
      dm_form_skill_label: "Навык",
      dm_form_cefr_label: "Уровень CEFR",
      dm_form_q_label: "Текст вопроса / инструкция *",
      dm_form_opts_label: "Варианты ответа * (отметьте верный)",
      dm_form_add_opt: "+ Добавить вариант",
      dm_form_rationale_label: "Пояснение (почему ответ верный)",
      dm_form_audio_toggle: "🎧 Прикрепить аудио к вопросу",
      dm_form_audio_ai: "🤖 Ввести текст — озвучит ИИ",
      dm_form_audio_file: "📁 Загрузить готовый аудиофайл",
      dm_form_audio_text_label: "Текст для аудирования — синтез речи ИИ",
      dm_form_tts_btn: "🔊 Прослушать",
      btn_cancel: "Отмена",
      btn_save: "💾 Сохранить",
      dm_sec_survey_title: "2. Вопросы когнитивно-аффективной анкеты (FLCAS)",
      dm_survey_desc: "Каждый вопрос оценивается по шкале Лайкерта (1–5). Измерение определяет влияние на профиль: тревожность (FLCAS), когнитивная емкость, темп, автономия, мотивация.",
      dm_form_new_survey: "Новый вопрос анкеты",
      dm_survey_dim_label: "Шкала (влияние на профиль)",
      dm_survey_weight_label: "Вес (0.1–3.0)",
      dm_survey_prompt_uz_label: "Вопрос (на узбекском) *",
      dm_survey_prompt_en_label: "Вопрос (на английском, необязательно)",
      low_bandwidth_on: "⚡ Экономный режим: ВКЛ",
      low_bandwidth_off: "⚡ Экономный режим",
      offline_notice: "⚠️ Ограниченное интернет-соединение: работа в режиме локального кэша.",
      ai_origin_badge: "🤖 Материал сгенерирован ИИ • Модель: TAAM-AI • Прозрачность: 100%",
      stage_1: "1-й этап: Цель и ориентация урока",
      stage_2: "2-й этап: Лексико-структурный скаффолдинг",
      stage_3: "3-й этап: Самостоятельное высказывание (ИИ заблокирован)",
      stage_4: "4-й этап: Анализ ошибок и L1-интерференция",
      stage_5: "5-й этап: Метакогнитивная рефлексия",
      skill_writing: "✍️ Письменная речь (Writing)",
      skill_speaking: "🎙️ Устная речь (Speaking)",
      skill_listening: "🎧 Аудирование (Listening)",
      skill_reading: "📖 Чтение (Reading)",
      btn_start_record: "🎙️ Начать запись голоса",
      btn_stop_record: "⏹️ Остановить и сохранить",
      btn_eval_speaking: "🤖 Оценить устную речь с помощью ИИ",
      btn_play_audio: "▶️ Прослушать аудио",
      btn_pause_audio: "⏸️ Пауза",
      consent_title: "Согласие на участие в исследовании и декларация академической честности",
      consent_accept: "Согласен и принимаю",
      research_title: "Глава IV докторской диссертации (DSc): Модуль математико-статистического анализа",
      research_sub: "Икрамова Азиза Аминовна — «Совершенствование методики обучения английскому языку на основе технологий искусственного интеллекта»",
      btn_export_word: "📥 Таблицы для диссертации (.docx)",
      btn_export_excel: "📊 Полная статистика (.xlsx)",
      btn_export_csv: "📄 Экспорт в CSV",
      tab_4_2: "Таблица 4.2. Распределение выборки",
      tab_4_4: "Таблица 4.4. Исходная эквивалентность",
      tab_4_5: "Таблица 4.5. Внутригрупповая динамика",
      tab_4_6: "Таблица 4.6. Речевые навыки",
      tab_4_7: "Таблица 4.7. Метапознание",
      tab_4_8: "Таблица 4.8. Коэффициент Беспалько К",
      tab_4_9: "Таблица 4.9. Итоговые выводы",
      prof_banner_free_desc: "С тарифом PRO используйте неограниченные ИИ-тесты, презентации и глубокую аналитику.",
      prof_banner_pro_desc: "Вам доступны все инструменты ИИ, тесты, презентации и полная аналитика без ограничений.",
      prof_btn_upgrade: "👑 Перейти на PRO",
      prof_btn_active: "👑 PRO Активен",
      prof_cefr_desc: "Уровень CEFR не усредняется, каждый речевой навык измеряется в индивидуальной динамике.",
      prof_esp_subtitle: "Интегрированные профессиональные модули:",
      prof_esp_modules: "• Методика наблюдения и анализа уроков<br>• Педагогический дискурс и формулирование инструкций<br>• Рубрики оценивания и критерии",
      prof_esp_footer: "Изучение языка гармонизировано с методикой его преподавания.",
      prof_cog_load: "Объём когнитивной нагрузки",
      prof_cog_pace: "Темп выполнения",
      prof_cog_anxiety: "Языковая тревожность (FLCAS)",
      prof_cog_autonomy: "Готовность к автономии",
      prof_cog_footer: "Измеряется на основе объективного поведения. Ненаучные тесты (VARK) исключены.",
      skill_listening_label: "Аудирование",
      skill_reading_label: "Чтение",
      skill_speaking_label: "Устная речь",
      skill_writing_label: "Письменная речь",
      path_subtitle: "Сейчас идёт 4-я неделя · Нажмите на строку, чтобы открыть страницу занятия",
      path_chip_approved: "Утверждено преподавателем",
      path_scaffolding_why: "<b>Динамика снижения педагогической поддержки (Scaffolding)</b><br>При успешном выполнении этапа самостоятельной работы в течение 3 занятий подряд уровень поддержки снижается на один шаг: <i>полная поддержка → частичная → автономный режим</i>. Каждое изменение утверждается преподавателем.",
      lesson_back_path: "← Вернуться к 16-недельной траектории",
      lesson_skill_label: "Вид речевой деятельности:",
      lesson_stage_1: "1. Введение",
      lesson_stage_2: "2. Подготовка",
      lesson_stage_3: "3. Самостоятельная работа (ИИ заблокирован)",
      lesson_stage_4: "4. Анализ и обратная связь",
      lesson_stage_5: "5. Рефлексия",
      btn_finish_prod: "Завершить работу и перейти к анализу →",
      ai_lock_title: "1-Е ПРАВИЛО: Помощь ИИ закрыта",
      ai_lock_desc: "На этом этапе система не даёт готовых ответов. Навык формируется только когда студент создаёт высказывание собственными интеллектуальными усилиями.",
      btn_lock_gen: "Генерация текста",
      btn_lock_trans: "Перевод",
      btn_lock_cont: "Продолжить текст",
      btn_lock_ans: "Готовый ответ",
      allowed_tools_title: "Разрешённые инструменты",
      btn_review_prompt: "Перечитать условие задания",
      btn_glossary: "Собственный глоссарий",
      btn_archive: "Архив предыдущих работ",
      diag_subtitle: "Определение 4 речевых навыков по CEFR и профиля тревожности FLCAS",
      diag_subj_label: "📚 Диагностика по предмету:",
      diag_subj_hint: "При выборе предмета отображаются относящиеся к нему навыки и вопросы.",
      diag_skills_label: "🎯 Навыки предмета:",
      diag_sec1_title: "1. Диагностический тест (4 навыка CEFR)",
      diag_sec2_title: "2. Когнитивно-аффективная анкета (шкала FLCAS)",
      diag_sec2_desc: "Оцените степень согласия с утверждениями по шкале от 1 до 5 (1 — Полностью не согласен, 5 — Полностью согласен):",
      btn_submit_diag: "📤 Отправить результаты диагностики и анкеты (обновить профиль) →",
      sm_title: "📚 Самостоятельные задания",
      sm_desc: "Сначала выберите предмет, затем решайте тесты, изучайте презентации и выполняйте письменные задания преподавателя",
      btn_refresh: "Обновить",
      sm_select_subject_label: "📖 Выберите учебный предмет:",
      sm_opt_all_subjects: "📂 Список предметов (выберите предмет)",
      sm_search_label: "🔍 Поиск по теме или названию:",
      sm_search_placeholder: "Например: Морфология, CEFR, Тест...",
      sm_tab_all: "Все",
      sm_tab_test: "📝 Тесты",
      sm_tab_presentation: "🖥️ Слайды",
      sm_tab_writing: "✍️ Письменные задания",
      sm_tab_plan: "📄 Планы уроков",
      prof_why_box: "<b>Основание Правила 2: Почему профиль и траектория сформированы именно так?</b><br>У студента показатель устной речи наименее развит (A2), а языковая тревожность повышена (71/100). Поэтому на 1-й неделе устные задания заменены аудированием. Упражнения по говорению вводятся постепенно со 2-й недели в безопасной диалоговой среде с правом на ошибку.",
      prof_anx_high: "Высокий",
      prof_anx_med: "Средний",
      prof_anx_low: "Низкий",
      path_scaffold_none: "без поддержки",
      path_scaffold_partial: "частичная поддержка",
      path_scaffold_full: "полная поддержка",
      path_status_done: " · ✅ завершено",
      path_status_active: " · ▶ текущее",
      path_action_lesson: "Занятие →",
      path_week_suffix: "-я неделя",
      path_weeks_label: "Недели",
      lesson_timer_rem: "Оставшееся время:",
      lesson_stage1_title: "1-й этап: Цель и ориентация урока",
      lesson_stage1_next: "Перейти к этапу подготовки →",
      lesson_stage2_title: "2-й этап: Лексико-структурный скаффолдинг",
      lesson_stage2_desc: "Перед самостоятельным письмом ознакомьтесь со следующими академическими словосочетаниями:",
      lesson_stage2_sample: "Образец структуры",
      lesson_stage2_sample_body: "1. Введение: Ключевая проблема оценивания письменной речи.<br>2. Основная часть: Анализ 2–3 важных критериев.<br>3. Заключение: Ответственность преподавателя за объективную оценку.",
      lesson_stage2_next: "Перейти к самостоятельной работе (ИИ блокируется) →",
      lesson_stage2_ai_title: "DeepSeek ИИ-Помощник (2-й этап)",
      lesson_stage2_ai_desc: "Запросите академическую структуру или направляющий пример перед началом самостоятельной работы.",
      lesson_stage2_ai_btn: "Запросить образец / план ✨",
      lesson_stage3_task_title: "Самостоятельное задание",
      lesson_stage3_editor_placeholder: "Пишите текст исключительно самостоятельно. На этом этапе инструменты искусственного интеллекта отключены...",
      lesson_stage3_auto_save: "Текст сохраняется автоматически",
      lesson_stage3_chars: "символов",
      lesson_stage3_words: "слов",
      lesson_stage3_lines: "строк",
      lesson_stage4_title: "4-й этап: Анализ текста и обоснованные комментарии",
      lesson_stage4_desc: "Система не даёт готовых исправлений, а указывает на причины ошибок. Выразите своё отношение к каждому комментарию.",
      lesson_stage4_why: "<b>Правило обратной связи системы</b><br>Комментарии сформированы по модели Hattie & Timperley. Интерференция родного языка (перенос синтаксиса родного языка в английский) выделена особо. Окончательное решение по редактированию остаётся за студентом.",
      lesson_stage4_ai_deep: "Глубокий лингвистический анализ с DeepSeek AI",
      lesson_stage4_next: "Перейти к рефлексии →",
      lesson_stage5_step1_title: "1-й шаг · Самооценка (Метакогнитивная оценка)",
      lesson_stage5_step1_desc: "Сначала честно оцените себя. Оценка ИИ откроется только после этого и никак не повлияет на вашу самооценку.",
      crit_content: "Полнота содержания",
      crit_grammar: "Грамматическая точность",
      crit_lexis: "Лексическое богатство",
      crit_coherence: "Связность и логика",
      lesson_stage5_rule4_hint: "После оценки всех четырёх критериев откроется оценка ИИ для сопоставительного анализа (Правило 4).",
      lesson_stage5_step2_title: "2-й шаг · Оценка ИИ и сопоставление",
      lesson_stage5_step2_desc: "Искусственный интеллект независимо оценивает вашу работу по 4 критериям и показывает причину каждого балла.",
      lesson_stage5_locked_ai: "🔒 <b>Оценка ИИ заблокирована</b><br>Как только вы выставите самооценку, рядом откроется оценка ИИ.",
      lesson_stage5_th_crit: "Критерий",
      lesson_stage5_th_you: "Вы",
      lesson_stage5_th_ai: "ИИ",
      lesson_stage5_th_diff: "Разница",
      lesson_stage5_gap_title: "Объясните причину расхождения своими словами:",
      lesson_stage5_gap_ph: "Почему ваша самооценка разошлась с фактическим результатом?",
      lesson_stage5_goal_title: "Личная цель на следующее занятие:",
      lesson_stage5_goal_ph: "Например: В следующий раз проверю текст на ошибки межъязыковой интерференции",
      lesson_stage5_btn_finish: "Завершить занятие",
      lesson_stage5_why: "<b>4-Е ПРАВИЛО: Сначала самооценка, затем оценка ИИ.</b><br>ИИ независимо оценивает работу и показывает обоснование, но никогда не заполняет самооценку за студента. Видя разницу между оценками, студент делает собственные выводы. Именно так формируются навыки саморегуляции и метакогнитивной рефлексии.",
      diag_likert_1: "Полностью не согласен",
      diag_likert_2: "Скорее не согласен",
      diag_likert_3: "Нейтрально",
      diag_likert_4: "Согласен",
      diag_likert_5: "Полностью согласен",
      diag_btn_play_audio: "Прослушать аудио",
      diag_btn_stop_audio: "Остановить",
      diag_audio_instruction: "🎧 Прослушайте аудио и выберите правильный вариант",
      diag_audio_playing: "Воспроизведение...",
      diag_q_label: "Вопрос",
      diag_survey_label: "Анкета",
      diag_all_skills: "📋 Все",
      sm_card_view: "Смотреть",
      sm_card_download: "Скачать",
      sm_card_read_plan: "Читать план",
      sm_card_take_test: "Пройти тест",
      sm_card_retake_test: "Пересдать",
      sm_card_start_writing: "Начать задание",
      sm_card_rewrite: "Переписать",
      sm_card_open_tasks: "Открыть задания →",
      sm_card_status_completed: "выполнено",
      sm_card_status_viewed: "👁️ Просмотрено",
      sm_card_status_pending: "⏳ Не выполнено",
      sm_card_subject_label: "Предмет",
      sm_card_topic_label: "Тема",
      sm_type_test: "Контрольный тест",
      sm_type_presentation: "Презентация (Слайды)",
      sm_type_writing: "Письменное задание",
      sm_type_plan: "План урока",
      sm_empty_subjects: "📂 Для вашей группы пока нет открытых предметов.",
      sm_empty_materials_title: "Учебные материалы не найдены",
      sm_empty_materials_search: "По вашему запросу ничего не найдено.",
      sm_empty_materials_none: "Преподаватель ещё не создал тесты или слайды по этому предмету.",
      sm_unit_materials: "материалов",
      sm_unit_topics: "тем",
      sm_done_label: "Выполнено",
      st_test_modal_title: "Контрольное тестирование",
      st_test_modal_desc: "Интерактивная проверка знаний по теме",
      st_test_modal_count_label: "Вопросы:",
      btn_exit: "Выход",
      st_test_submit_btn: "✅ Завершить тест и проверить результат",
      st_slide_modal_title: "Презентация",
      st_slide_img_loading: "🎨 Подготовка изображения...",
      st_slide_speaker_notes_label: "🎙️ Заметки докладчика (Speaker Notes):",
      st_slide_prompt_label: "🖼️ Промпт для генерации изображения (Midjourney/DALL-E):",
      st_slide_download_btn: "📥 Скачать презентацию (HTML/PDF)",
      st_slide_copy_btn: "📋 Копировать текст",
      st_slide_prev_btn: "← Назад",
      st_slide_next_btn: "Вперёд →",
      st_writing_modal_title: "Письменное задание",
      st_writing_rubric_summary: "📏 Критерии оценивания (4 критерия × 5 баллов)",
      st_writing_editor_label: "✍️ Ваш текст",
      st_writing_self_rating_title: "🪞 Самооценка (1–5): оцените свою работу перед отправкой",
      st_writing_submit_btn: "📤 Отправить и получить оценку ИИ",
      st_plan_modal_title: "План урока (Lesson Plan)",
      st_plan_modal_desc: "Поурочная технологическая карта занятия",
      st_plan_copy_btn: "📋 Скопировать план",
      btn_close: "Закрыть",
      nav_proposals: "Предложения и отзывы",
      prop_page_title: "💡 Центр предложений и педагогического контроля",
      prop_page_desc: "Обмен предложениями между преподавателями и студентами, рекомендации ИИ и педагогические решения (Правило 3)",
      btn_send_proposal: "Отправить новое предложение",
      prop_tab_all: "Все",
      prop_tab_inbox: "Входящие",
      prop_tab_sent: "Исходящие",
      prop_tab_system: "Система (ИИ)",
      prop_filter_direction: "Направление:",
      prop_filter_status: "Статус:",
      prop_modal_title: "Отправить новое предложение",
      prop_modal_desc: "Обмен мнениями с преподавателями и студентами, внесение методических или учебных предложений",
      prop_rec_type_label: "👥 Категория получателя:",
      prop_rec_person_label: "👤 Выберите получателя:",
      prop_direction_label: "🔄 Направление предложения:",
      prop_cat_label: "🏷️ Категория предложения:",
      prop_title_label: "📝 Тема предложения (Кратко и ясно) *:",
      prop_text_label: "💬 Полный текст и содержание предложения *:",
      prop_basis_label: "🎯 Обоснование или ожидаемый результат:",
      btn_submit_proposal: "Отправить предложение",
      prop_decision_title: "Решение по предложению",
      prop_decision_desc: "Вы можете добавить педагогический комментарий или рекомендацию к решению",
      prop_decision_comment_label: "✍️ Комментарий / Педагогическое замечание (необязательно):",
      nav_dev_api: "Разработчик и API",
      nav_api_docs: "Документация API (Docs)",
      btn_api_docs: "API Docs",
      api_docs_title: "⚡ Документация RESTful API & OpenAPI TILORA",
      api_docs_subtitle: "117 эндпоинтов · Безопасность JWT · 4 педагогических принципа · Статистика DSc · Интеграция со Swagger UI и ReDoc",
      api_tab_catalog: "Каталог эндпоинтов",
      api_tab_tester: "Интерактивный тестер API (Консоль)",
      api_tab_arch: "Архитектура и 4 принципа",
      api_tab_swagger: "Встроенный Swagger UI",
      api_tab_keys: "Ключи API (Keys)",
      api_keys_sec_title: "🔑 Ключи API для программной интеграции",
      api_keys_sec_desc: "Ключи доступа для Разработчиков (Developer) и Супер Администратора (Admin) для подключения внешних систем, мобильных приложений и скриптов",
      btn_create_api_key: "Создать новый ключ API",
      api_stat_total_keys: "Всего ключей API",
      api_stat_active_keys: "Активные ключи",
      api_stat_revoked_keys: "Отозванные / Истёкшие",
      api_keys_table_title: "Список существующих ключей API",
      api_keys_guide_title: "Как использовать ключ API?",
      modal_api_key_title: "Создание нового ключа API",
      modal_api_key_desc: "Безопасный ключ для интеграции внешних сервисов, мобильных приложений и скриптов",
      modal_api_key_name_label: "📝 Название ключа (Цель использования) *:"
    }
  };

  let currentLang = localStorage.getItem('tilora_lang') || 'uz';
  let isLowBandwidth = localStorage.getItem('tilora_low_bandwidth') === 'true';

  // ==========================================
  // 2. TIL ALMASHTIRISH FUNKSIYALARI
  // ==========================================
  window.switchLanguage = function(lang) {
    if (!I18N_DICT[lang]) return;
    currentLang = lang;
    localStorage.setItem('tilora_lang', lang);
    applyTranslations();
  };

  function applyTranslations() {
    const dict = I18N_DICT[currentLang] || I18N_DICT.uz;
    
    // Tugmalarning faolligini yangilash
    document.querySelectorAll('.lang-btn').forEach(btn => {
      if (btn.getAttribute('data-lang') === currentLang) {
        btn.classList.add('active');
        btn.style.background = 'var(--teal)';
        btn.style.color = '#fff';
      } else {
        btn.classList.remove('active');
        btn.style.background = 'none';
        btn.style.color = 'var(--ink)';
      }
    });

    // Sarlavhalar va taglinelar
    const brandTagline = document.querySelector('.sidebar .tagline');
    if (brandTagline) brandTagline.textContent = dict.brand_tagline;

    const pageMainHeading = document.getElementById('pageMainHeading');
    if (pageMainHeading) pageMainHeading.textContent = dict.page_title;

    const pageSubHeading = document.getElementById('pageSubHeading');
    if (pageSubHeading) pageSubHeading.textContent = dict.page_subtitle;

    // Tejamkor rejim tugmasi
    const lbText = document.getElementById('lowBandwidthText');
    if (lbText) lbText.textContent = isLowBandwidth ? dict.low_bandwidth_on : dict.low_bandwidth_off;

    // Offline banner
    const offText = document.getElementById('offlineNoticeText');
    if (offText) offText.textContent = dict.offline_notice;

    // Sidebar guruh sarlavhalari
    const secTitles = document.querySelectorAll('.sidebar .nav-section-title');
    if (secTitles.length >= 4) {
      secTitles[0].textContent = dict.nav_student_room;
      secTitles[1].textContent = dict.nav_teacher_room;
      secTitles[2].textContent = dict.nav_research_room;
      secTitles[3].textContent = dict.nav_admin_room;
    }

    // data-i18n atributiga ega barcha elementlar
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        if (dict[key].includes('<') || el.getAttribute('data-i18n-html') === 'true') {
          el.innerHTML = dict[key];
        } else {
          el.textContent = dict[key];
        }
      }
    });

    // Kirish / Chiqish tugmasi matni
    const btnAuth = document.getElementById('btnLoginLogout');
    if (btnAuth) {
      const stateObj = window.STATE || (typeof STATE !== 'undefined' ? STATE : null);
      const isLogged = !!(stateObj && stateObj.currentUser && stateObj.token);
      if (isLogged) {
        btnAuth.innerHTML = `<span>${dict.logout_btn || 'Chiqish'}</span>`;
        btnAuth.setAttribute('title', dict.logout_btn || 'Chiqish');
      } else {
        btnAuth.innerHTML = `<span style="font-size:13px;margin-right:5px">🔑</span><span>${dict.login_btn || 'Profilga kirish'}</span>`;
        btnAuth.setAttribute('title', dict.login_btn || 'Profilga kirish');
      }
    }

    // Foydalanuvchi roli nomi
    const navRole = document.getElementById('userNavRole');
    const stateObj = window.STATE || (typeof STATE !== 'undefined' ? STATE : null);
    if (navRole && stateObj && stateObj.currentUser) {
      const r = stateObj.currentUser.role;
      const group = stateObj.currentUser.group_name || '';
      if (r === 'student') {
        navRole.textContent = currentLang === 'ru' ? `Студент · ${group || 'Группа'}` : (currentLang === 'en' ? `Student · ${group || 'Group'}` : `Talaba · ${group || 'Guruh'}`);
      } else if (r === 'teacher') {
        navRole.textContent = currentLang === 'ru' ? 'Преподаватель' : (currentLang === 'en' ? 'Teacher' : "O'qituvchi");
      } else if (r === 'researcher') {
        navRole.textContent = currentLang === 'ru' ? 'Исследователь' : (currentLang === 'en' ? 'Researcher' : 'Tadqiqotchi');
      } else if (r === 'admin') {
        navRole.textContent = currentLang === 'ru' ? 'Администратор' : (currentLang === 'en' ? 'Administrator' : 'Administrator');
      }
    }

    // Diagnostika va anketa boshqaruvi ekranini qayta chizish
    if (typeof window.dmRerender === 'function') {
      window.dmRerender();
    }

    // Qidiruv va dars inputlarining placeholderlarini yangilash
    const searchInput = document.getElementById('studentMaterialSearchInput');
    if (searchInput && dict.sm_search_placeholder) {
      searchInput.setAttribute('placeholder', dict.sm_search_placeholder);
    }
    const prodText = document.getElementById('productionText');
    if (prodText && dict.lesson_stage3_editor_placeholder) {
      prodText.setAttribute('placeholder', dict.lesson_stage3_editor_placeholder);
    }
    const refGap = document.getElementById('reflectionGapInput');
    if (refGap && dict.lesson_stage5_gap_ph) {
      refGap.setAttribute('placeholder', dict.lesson_stage5_gap_ph);
    }
    const refGoal = document.getElementById('reflectionGoalInput');
    if (refGoal && dict.lesson_stage5_goal_ph) {
      refGoal.setAttribute('placeholder', dict.lesson_stage5_goal_ph);
    }

    // Dars ko'nikmasi promptini joriy tilda yangilash
    if (typeof window.switchLessonSkill === 'function') {
      window.switchLessonSkill(currentLessonSkill || 'writing');
    }

    // 16-haftalik o'quv yo'lini qayta chizish
    if (typeof window.renderLearningPath === 'function') {
      window.renderLearningPath();
    }

    // Talabalar mustaqil topshiriqlari kartalari va filtrlarini qayta chizish
    if (typeof window.renderStudentSubjectCards === 'function') {
      window.renderStudentSubjectCards();
    }
    if (typeof window.filterStudentMaterialsDisplay === 'function') {
      window.filterStudentMaterialsDisplay();
    }
    if (typeof window.updateStudentMaterialCounters === 'function') {
      window.updateStudentMaterialCounters();
    }

    // Diagnostika va anketa savollarini qayta chizish
    if (typeof window.reloadDiagnosticQuestions === 'function') {
      window.reloadDiagnosticQuestions();
    } else if (typeof window.renderDiagnosticQuestions === 'function') {
      const dBox = document.getElementById('diagnosticQuestionsContainer');
      const sBox = document.getElementById('surveyQuestionsContainer');
      if (dBox) window.renderDiagnosticQuestions(dBox);
      if (sBox && typeof window.renderSurveyQuestions === 'function') window.renderSurveyQuestions(sBox);
    }
    if (typeof window.renderDiagSubjectBar === 'function') {
      window.renderDiagSubjectBar();
    }

    // Profil ko'rsatkichlari va tushuntirishini yangilash
    if (typeof window.loadUserProfile === 'function' && window.STATE && window.STATE.token) {
      window.loadUserProfile();
    }

    // Ochiq slayd bo'lsa uni ham yangilash
    if (typeof window.renderCurrentStudentSlide === 'function' && window.STATE && window.STATE.studentPresentation) {
      window.renderCurrentStudentSlide();
    }
  }

  window.applyTranslations = applyTranslations;
  window.I18N_DICT = I18N_DICT;
  window.getCurrentLang = function() {
    return currentLang || localStorage.getItem('tilora_lang') || 'uz';
  };
  window.getI18nText = function(key, fallback) {
    const lang = window.getCurrentLang();
    const d = I18N_DICT[lang] || I18N_DICT.uz;
    return (d && d[key]) || fallback || key;
  };

  // ==========================================
  // 3. TEJAMKOR VA OFLAYN REJIM (Low-Bandwidth)
  // ==========================================
  window.toggleLowBandwidthMode = function() {
    isLowBandwidth = !isLowBandwidth;
    localStorage.setItem('tilora_low_bandwidth', isLowBandwidth ? 'true' : 'false');
    applyLowBandwidthState();
    
    const msg = isLowBandwidth 
      ? (currentLang === 'en' ? 'Low-bandwidth mode enabled. Heavy media disabled.' : (currentLang === 'ru' ? 'Экономный режим включен. Тяжелые медиафайлы отключены.' : 'Tejamkor rejim yoqildi. Ovoz va og\'ir media fayllar yuklanishi to\'xtatildi.'))
      : (currentLang === 'en' ? 'Standard bandwidth mode restored.' : (currentLang === 'ru' ? 'Стандартный режим восстановлен.' : 'Standart to\'liq rejim qaytarildi.'));
    
    if (window.showToast) window.showToast(msg, 'info');
    applyTranslations();
  };

  function applyLowBandwidthState() {
    if (isLowBandwidth) {
      document.body.classList.add('low-bandwidth-active');
      const audios = document.querySelectorAll('audio');
      audios.forEach(a => a.preload = 'none');
    } else {
      document.body.classList.remove('low-bandwidth-active');
    }
  }

  // Oflayn voqealari tinglash
  window.addEventListener('offline', () => {
    const b = document.getElementById('offlineNoticeBanner');
    if (b) b.style.display = 'block';
  });

  window.addEventListener('online', () => {
    const b = document.getElementById('offlineNoticeBanner');
    if (b) b.style.display = 'none';
  });

  // ==========================================
  // 4. DISSERTATSIYA 4-BOBI TADQIQOTCHI PANELI
  // ==========================================
  // Jadvallar manbadan qat'i nazar `currentResearchData` dan chiziladi:
  //   'dissertation' → GET /research/tables (statik, oldindan hisoblangan to'plam)
  //   'live'         → GET /research/live/tables (platformadagi assessments dan real vaqtda)
  let currentResearchData = null;
  let researchSource = 'dissertation';
  let liveOverview = null;
  let activeResearchTab = 'tab_4_2';
  const esc = window.escapeHtml || (s => String(s == null ? '' : s));
  const rArg = (v) => (typeof window.jsArg === 'function' ? window.jsArg(v) : esc(JSON.stringify(String(v == null ? '' : v))));
  const LIVE_ROLES = ['researcher', 'teacher', 'admin'];
  const rToast = (msg, type) => { if (typeof window.showToast === 'function') window.showToast(msg, type || 'info'); };

  function researchApiBase() {
    return (window.STATE && STATE.apiBaseUrl ? STATE.apiBaseUrl : '/api');
  }
  function researchToken() {
    return (window.STATE && STATE.token) ? STATE.token : (localStorage.getItem('tilora_token') || '');
  }
  function researchAuthHeaders() {
    const h = {};
    const t = researchToken();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  }
  function researchRole() {
    return (window.STATE && STATE.currentUser) ? (STATE.currentUser.role || '') : '';
  }
  function canUseLiveResearch() {
    return !!researchToken() && LIVE_ROLES.includes(researchRole());
  }
  function researchSourceQuery() {
    return researchSource === 'live' ? '?source=live' : '';
  }
  function researchDetail(data, status) {
    if (!data) return 'HTTP ' + status;
    const d = data.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map(x => ((x.loc && x.loc.length) ? x.loc[x.loc.length - 1] + ': ' : '') + (x.msg || '')).join('; ');
    return data.message || ('HTTP ' + status);
  }
  // JSON so'rov (body: obyekt → JSON; FormData → multipart). Xatoda Error(detail) tashlaydi.
  async function researchRequest(path, opts) {
    opts = opts || {};
    const headers = researchAuthHeaders();
    let body = opts.body;
    if (body !== undefined && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }
    const res = await fetch(researchApiBase() + path, { method: opts.method || 'GET', headers, body });
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const err = new Error(researchDetail(data, res.status));
      err.status = res.status;
      throw err;
    }
    return data;
  }
  function researchNotice(html, tone) {
    const bg = tone === 'error' ? 'var(--clay-soft, #F6E7E2)' : (tone === 'ok' ? 'var(--teal-soft)' : 'var(--amber-soft)');
    const col = tone === 'error' ? 'var(--clay)' : (tone === 'ok' ? 'var(--teal)' : '#5F4A0F');
    return '<div style="padding:12px 16px;border-radius:9px;background:' + bg + ';border:1px solid var(--line);color:' + col + ';font-size:13px;line-height:1.55">' + html + '</div>';
  }
  function effectLabel(d) {
    const v = Math.abs(Number(d) || 0);
    if (v >= 0.8) return 'Katta effekt (Large > 0.8)';
    if (v >= 0.5) return "O'rta effekt (Medium 0.5–0.8)";
    if (v >= 0.2) return 'Kichik effekt (Small 0.2–0.5)';
    return 'Ahamiyatsiz effekt (< 0.2)';
  }

  // Manba almashtirish: "📚 Dissertatsiya to'plami" | "🟢 Jonli platforma ma'lumotlari"
  window.setResearchSource = function(src) {
    researchSource = (src === 'live') ? 'live' : 'dissertation';
    document.querySelectorAll('.res-src-btn').forEach(b => {
      const on = b.getAttribute('data-source') === researchSource;
      b.classList.toggle('active', on);
      b.style.background = on ? 'var(--teal)' : 'var(--surface-2)';
      b.style.color = on ? '#fff' : 'var(--ink)';
    });
    const liveArea = document.getElementById('researchLiveArea');
    const banner = document.getElementById('researchLiveBanner');
    const badge = document.getElementById('researchSourceBadge');
    const tcBox = document.getElementById('researchTeacherCompetence');
    if (liveArea) liveArea.style.display = 'none';
    if (tcBox) tcBox.style.display = 'none';
    if (banner) banner.style.display = researchSource === 'live' ? 'block' : 'none';
    if (badge) badge.textContent = researchSource === 'live' ? "Platformadagi pre/mid/post baholar — real vaqtda hisoblanadi" : "Oldindan hisoblangan yakuniy natijalar (2024–2026)";
    const container = document.getElementById('dissertationTablesArea');
    if (container) container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Jadvallar yuklanmoqda...</div>';
    window.initResearchDashboard();
  };

  window.initResearchDashboard = async function() {
    if (researchSource === 'live') { await loadLiveResearch(); return; }
    try {
      const res = await fetch(researchApiBase() + '/research/tables', { headers: researchAuthHeaders() });
      if (res.ok) {
        currentResearchData = await res.json();
        updateResearchKpis();
        renderResearchTables();
      }
    } catch (e) {
      console.warn("Tadqiqot ma'lumotlarini yuklashda xatolik:", e);
    }
  };

  async function loadLiveResearch() {
    const banner = document.getElementById('researchLiveBanner');
    const container = document.getElementById('dissertationTablesArea');
    const liveArea = document.getElementById('researchLiveArea');
    if (!canUseLiveResearch()) {
      currentResearchData = null;
      const msg = !researchToken()
        ? "Jonli ma'lumotlar faqat tizimga kirgan <b>tadqiqotchi</b>, <b>o'qituvchi</b> yoki <b>administrator</b> uchun ochiq. Iltimos, avval tizimga kiring."
        : "Sizning rolingiz (<b>" + esc(researchRole() || "noma'lum") + "</b>) jonli tadqiqot ma'lumotlarini ko'rishga ruxsat bermaydi (kerak: researcher / teacher / admin).";
      if (banner) { banner.style.display = 'block'; banner.innerHTML = researchNotice('🔒 ' + msg, 'warn'); }
      if (container) container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">Jonli jadvallar uchun ruxsat yo\'q. «📚 Dissertatsiya to\'plami» manbasini tanlang.</div>';
      if (liveArea) liveArea.style.display = 'none';
      const tcBox = document.getElementById('researchTeacherCompetence');
      if (tcBox) tcBox.style.display = 'none';
      updateResearchKpis();
      return;
    }
    try {
      const [ov, tables] = await Promise.all([
        researchRequest('/research/live/overview'),
        researchRequest('/research/live/tables'),
      ]);
      liveOverview = ov;
      currentResearchData = tables;
      renderLiveBanner(ov, tables);
      renderTeacherCompetence(ov.teacher_competence);
      updateResearchKpis();
      renderResearchTables();
      if (liveArea) liveArea.style.display = 'block';
      fillResearchSkillSelect(ov.skills || []);
      window.researchReloadAssessments();
      loadProcessIndicators();
      loadReliability();
      loadSillSummary();
      loadRetentionCard();
    } catch (e) {
      currentResearchData = null;
      if (banner) { banner.style.display = 'block'; banner.innerHTML = researchNotice("Jonli ma'lumotlarni yuklab bo'lmadi: " + esc(e.message), 'error'); }
      if (container) container.innerHTML = '';
      updateResearchKpis();
    }
  }

  // To'liqlik banneri (completeness): tayyor → yashil, aks holda amber + nima yetishmayotgani
  function renderLiveBanner(ov, tables) {
    const banner = document.getElementById('researchLiveBanner');
    if (!banner) return;
    const c = ov.completeness || {};
    const sum = (tables && tables.table_4_2 && tables.table_4_2.summary) || {};
    const arms = ov.groups_by_arm || {};
    const missing = [];
    if ((arms.experimental || 0) === 0) missing.push("tajriba (experimental) qanotidagi guruh yo'q");
    if ((arms.control || 0) === 0) missing.push("nazorat (control) qanotidagi guruh yo'q");
    if ((sum.experimental_total || 0) < 5) missing.push('tajriba guruhida kamida 5 talaba kerak (hozir ' + (sum.experimental_total || 0) + ')');
    if ((sum.control_total || 0) < 5) missing.push('nazorat guruhida kamida 5 talaba kerak (hozir ' + (sum.control_total || 0) + ')');
    if ((c.with_both || 0) < 10) missing.push('pre va post ikkalasi kiritilgan kamida 10 talaba kerak (hozir ' + (c.with_both || 0) + ')');
    if ((c.with_metacognitive || 0) === 0) missing.push("metakognitiv shkala (meta_*) baholari kiritilmagan — 4.7 va 4.9 jadvallar to'liq bo'lmaydi");
    const stats = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;font-size:12px">'
      + [['Qanotdagi talabalar', c.students_in_arms], ['Pre bor', c.with_pre], ['Post bor', c.with_post], ['Pre+Post', c.with_both], ['Metakognitiv', c.with_metacognitive], ['OTM', c.institutions], ['Baholar jami', ov.assessments_total], ["Mashg'ulot yozuvlari", ov.lesson_records_total]]
        .map(([k, v]) => '<span style="background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:3px 9px;color:var(--ink)"><b>' + esc(v == null ? 0 : v) + '</b> ' + esc(k) + '</span>').join('')
      + '</div>';
    const insts = (ov.institutions || []).map(i => esc(i.short_name || i.name)).join(', ');
    if (c.ready) {
      banner.innerHTML = researchNotice('<b>🟢 Ma\'lumotlar statistik tahlil uchun yetarli.</b> Jadvallar platformadagi haqiqiy pre/post baholardan hisoblandi.' + (insts ? ' OTMlar: ' + insts + '.' : '') + stats, 'ok');
    } else {
      banner.innerHTML = researchNotice('<b>🟡 Ma\'lumotlar hali to\'liq emas</b> — jadvallar hisoblanadi, lekin xulosalar dastlabki.<ul style="margin:6px 0 0;padding-left:18px">' + missing.map(m => '<li>' + esc(m) + '</li>').join('') + '</ul>' + stats, 'warn');
    }
    banner.style.display = 'block';
  }

  // O'qituvchilar SI-kompetensiyasi dinamikasi (Guskey 2-daraja) — overview.teacher_competence
  function renderTeacherCompetence(tc) {
    const box = document.getElementById('researchTeacherCompetence');
    if (!box) return;
    tc = tc || {};
    const comps = tc.components || {};
    const order = ['cognitive', 'didactic', 'ethical', 'reflective'].filter(k => comps[k]).concat(Object.keys(comps).filter(k => !['cognitive', 'didactic', 'ethical', 'reflective'].includes(k)));
    const th = 'padding:8px 10px;white-space:nowrap;font-size:12px;text-align:left';
    const td = 'padding:8px 10px;font-size:13px';
    const fmt = (v, d) => (v === null || v === undefined || v === '') ? '—' : (typeof v === 'number' ? v.toFixed(d) : String(v));
    const growthCell = (g) => {
      if (g === null || g === undefined || g === '—' || g === '') return '<span style="color:var(--muted)">—</span>';
      const n = Number(String(g).replace('%', '').replace('+', ''));
      const col = isNaN(n) ? 'var(--ink)' : (n > 0 ? '#16A34A' : (n < 0 ? 'var(--clay)' : 'var(--muted)'));
      return '<b style="color:' + col + '">' + (!isNaN(n) && n > 0 && !String(g).startsWith('+') ? '+' : '') + esc(g) + (typeof g === 'number' ? '%' : '') + '</b>';
    };
    let html = '<div class="card" style="padding:16px">'
      + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px">'
      + '<div style="font-weight:700;font-size:14px">👩‍🏫 O\'qituvchilar SI-kompetensiyasi dinamikasi (Guskey 2-daraja)</div>'
      + '<span class="chip none" style="padding:2px 9px">' + esc(tc.teachers || 0) + ' o\'qituvchi</span></div>'
      + '<p style="font-size:12.5px;color:var(--muted);margin:0 0 10px">Dissertatsiya 2.3 / UNESCO AI CFT 2024: o\'qituvchilarning o\'z-o\'zini baholash varaqasi (4 komponent, 1–5 shkala) bo\'yicha pre → post o\'zgarish, juftlashgan t-mezon.</p>';
    if (!(tc.teachers > 0)) {
      html += '<div style="font-size:12.5px;color:var(--muted);padding:12px;border:1px dashed var(--line);border-radius:8px;text-align:center">Hali birorta o\'qituvchi SI-kompetensiya varaqasini to\'ldirmagan. O\'qituvchilar kuzatuv panelidagi «🧠 SI-kompetensiyam» bo\'limida pre/post baholashni o\'tkazgach, dinamika shu yerda ko\'rinadi.</div>';
    } else {
      html += '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;min-width:620px"><thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">'
        + '<th style="' + th + '">Komponent</th><th style="' + th + ';text-align:center" title="pre va post ikkalasi bor o\'qituvchilar">n (juft)</th><th style="' + th + ';text-align:center">Pre (1–5)</th><th style="' + th + ';text-align:center">Post (1–5)</th><th style="' + th + ';text-align:center">O\'sish</th><th style="' + th + ';text-align:center">t</th><th style="' + th + ';text-align:center">p</th></tr></thead><tbody>';
      order.forEach(k => {
        const c = comps[k] || {};
        const sig = typeof c.p === 'string' && /<\s*0?\.0?5|<\s*0\.01|<\s*0\.001/.test(c.p);
        html += '<tr style="border-bottom:1px solid var(--line)"><td style="' + td + ';font-weight:600">' + esc(c.name || k) + '</td>'
          + '<td style="' + td + ';text-align:center">' + esc(c.n_paired == null ? 0 : c.n_paired) + '</td>'
          + '<td style="' + td + ';text-align:center">' + esc(fmt(c.pre, 2)) + '</td>'
          + '<td style="' + td + ';text-align:center;font-weight:700">' + esc(fmt(c.post, 2)) + '</td>'
          + '<td style="' + td + ';text-align:center">' + growthCell(c.growth) + '</td>'
          + '<td style="' + td + ';text-align:center">' + esc(fmt(c.t, 2)) + '</td>'
          + '<td style="' + td + ';text-align:center;' + (sig ? 'color:var(--teal);font-weight:700' : '') + '">' + esc(fmt(c.p)) + '</td></tr>';
      });
      html += '</tbody></table></div>'
        + '<div style="font-size:11.5px;color:var(--muted);margin-top:8px">n (juft) — pre va post ikkalasini to\'ldirgan o\'qituvchilar; t va p — juftlashgan t-mezon (n ≥ 2 bo\'lganda). O\'sish — post va pre o\'rtachalari farqi (%).</div>';
    }
    box.innerHTML = html + '</div>';
    box.style.display = 'block';
  }

  // KPI kartalari (N, χ² p, Cohen's d, K_s) — ikkala rejimda yuklangan ma'lumotdan
  function updateResearchKpis() {
    const d = currentResearchData;
    const set = (id, html) => { const el = document.getElementById(id); if (el) el.innerHTML = html; };
    const note = document.getElementById('researchDataSourceNote');
    if (!d) {
      set('kpiNValue', 'N = —'); set('kpiNSub', "Ma'lumot yuklanmagan");
      set('kpiChiValue', 'p = —'); set('kpiChiSub', '—');
      set('kpiDValue', 'd = —'); set('kpiDSub', '—');
      set('kpiKsValue', 'K_s = —'); set('kpiKsSub', '—');
      if (note) note.textContent = '';
      return;
    }
    const s = (d.table_4_2 && d.table_4_2.summary) || {};
    const nInst = (d.table_4_2 && d.table_4_2.rows) ? d.table_4_2.rows.length : 0;
    set('kpiNValue', 'N = ' + esc(s.grand_total == null ? '—' : s.grand_total));
    set('kpiNSub', 'Tajriba: ' + esc(s.experimental_total == null ? '—' : s.experimental_total) + ' | Nazorat: ' + esc(s.control_total == null ? '—' : s.control_total) + '<br><b>' + (researchSource === 'live' ? esc(nInst) + ' ta OTM (jonli)' : 'BuxDU asosiy baza: N=90') + '</b>');

    const o4 = (d.table_4_4 && d.table_4_4.overall) || {};
    const p = (typeof o4.p_value === 'number') ? o4.p_value : null;
    set('kpiChiValue', 'p = ' + esc(p == null ? '—' : p));
    set('kpiChiSub', 'χ² = ' + esc(o4.chi2 == null ? '—' : o4.chi2) + ', df = ' + esc(o4.df == null ? '—' : o4.df) + (p == null ? '' : (p > 0.05 ? ' (p > 0.05)' : ' (p ≤ 0.05)')) + '<br><b>' + esc(o4.conclusion || (p == null ? "Ma'lumot yetarli emas" : (p > 0.05 ? 'Guruhlar tengligi tasdiqlandi' : "Boshlang'ich farq mavjud"))) + '</b>');

    const avgD = d.table_4_7 ? d.table_4_7.average_d : null;
    set('kpiDValue', 'd = ' + esc(avgD == null ? '—' : avgD));
    set('kpiDSub', esc(avgD == null ? '—' : effectLabel(avgD)) + '<br><b>' + (avgD == null ? "Ma'lumot yetarli emas" : (Math.abs(avgD) >= 0.8 ? 'Pedagogik yuqori samara' : (researchSource === 'live' ? "Metakognitiv komponentlar o'rtachasi (post, tajriba vs nazorat)" : 'Metakognitiv komponentlar o\'rtachasi'))) + '</b>');

    const o8 = (d.table_4_8 && d.table_4_8.overall) || {};
    set('kpiKsValue', 'K_s = ' + esc(o8.ratio_k == null ? '—' : o8.ratio_k));
    set('kpiKsSub', 'Bespalko mezoni (K > 1.0)<br><b>' + esc(o8.diff_percent ? o8.diff_percent + (String(o8.diff_percent).startsWith('+') ? " yuqori o'zlashtirish" : '') : '—') + '</b>');

    if (note) note.textContent = d.data_source_note ? ('ℹ️ ' + d.data_source_note) : '';
  }

  window.switchResearchTab = function(tabKey) {
    activeResearchTab = tabKey;
    document.querySelectorAll('.res-tab-btn[data-tab]').forEach(b => {
      if (b.getAttribute('data-tab') === tabKey) {
        b.classList.add('active');
        b.style.background = 'var(--teal)';
        b.style.color = '#fff';
      } else {
        b.classList.remove('active');
        b.style.background = 'var(--surface-2)';
        b.style.color = 'var(--ink)';
      }
    });
    renderResearchTables();
  };

  function researchTableMissing(container, what) {
    container.innerHTML = '<div style="text-align:center;padding:24px;color:var(--muted)">' + esc(what) + ' bu manbada mavjud emas.</div>';
  }

  function renderResearchTables() {
    const container = document.getElementById('dissertationTablesArea');
    if (!container) return;
    if (!currentResearchData) return;
    const researchTablesData = currentResearchData;

    if (activeResearchTab === 'tab_4_2') {
      const d = researchTablesData.table_4_2;
      if (!d) { researchTableMissing(container, '4.2-jadval'); return; }
      let html = `
        <div style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
          <h4 style="margin:0;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
          <span style="font-size:12px;background:var(--teal-soft);color:var(--teal);padding:3px 8px;border-radius:12px;font-weight:600">Jami N = ${esc(d.summary.grand_total)}</span>
        </div>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Oliy ta'lim muassasasi</th>
                <th style="padding:8px 12px">Ta'lim yo'nalishi</th>
                <th style="padding:8px 12px;text-align:center">Tajriba guruhi</th>
                <th style="padding:8px 12px;text-align:center">Nazorat guruhi</th>
                <th style="padding:8px 12px;text-align:center">Jami</th>
              </tr>
            </thead>
            <tbody>`;
      d.rows.forEach(r => {
        html += `
          <tr style="border-bottom:1px solid var(--line);height:40px">
            <td style="padding:8px 12px;font-weight:600">${esc(r.institution)}</td>
            <td style="padding:8px 12px;color:var(--muted);font-size:12.5px">${esc(r.specialty)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:var(--teal)">${esc(r.experimental)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700">${esc(r.control)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;background:var(--surface-2)">${esc(r.total)}</td>
          </tr>`;
      });
      html += `
          <tr style="background:#EBF5FF;font-weight:700;height:42px">
            <td style="padding:8px 12px">Jami</td>
            <td style="padding:8px 12px;color:var(--muted)">${esc(d.rows.length)} ta oliy ta'lim muassasasi</td>
            <td style="padding:8px 12px;text-align:center;color:var(--teal)">${esc(d.summary.experimental_total)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(d.summary.control_total)}</td>
            <td style="padding:8px 12px;text-align:center;font-size:15px;color:#1E40AF">${esc(d.summary.grand_total)}</td>
          </tr>
        </tbody>
      </table>
      </div>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_4') {
      const d = researchTablesData.table_4_4;
      if (!d) { researchTableMissing(container, '4.4-jadval'); return; }
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">OTM</th>
                <th style="padding:8px 12px">Guruh</th>
                <th style="padding:8px 12px;text-align:center">Yuqori (B2-C1)</th>
                <th style="padding:8px 12px;text-align:center">O'rta (B1)</th>
                <th style="padding:8px 12px;text-align:center">Quyi (A2)</th>
                <th style="padding:8px 12px;text-align:center">Jami</th>
                <th style="padding:8px 12px;text-align:center">Chi-Square (p-qiymat)</th>
              </tr>
            </thead>
            <tbody>`;
      d.rows.forEach(r => {
        html += `
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:8px 12px;font-weight:600" rowspan="2">${esc(r.institution)}</td>
            <td style="padding:8px 12px;color:var(--teal);font-weight:600">Tajriba</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.exp_high)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.exp_mid)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.exp_low)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:600">${esc(r.exp_total)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:${Number(r.p_value) > 0.05 ? 'var(--teal)' : 'var(--clay)'}" rowspan="2">χ² = ${esc(r.chi2)}<br><span style="font-size:12px;font-weight:400;color:var(--muted)">p = ${esc(r.p_value)} ${Number(r.p_value) > 0.05 ? '> 0.05' : '≤ 0.05'}</span></td>
          </tr>
          <tr style="border-bottom:1.5px solid var(--line);background:var(--surface-2)">
            <td style="padding:8px 12px;color:var(--muted);font-weight:600">Nazorat</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_high)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_mid)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_low)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:600">${esc(r.ctrl_total)}</td>
          </tr>`;
      });
      const ov = d.overall;
      if (ov) {
        html += `
          <tr style="background:#EBF5FF;font-weight:700">
            <td style="padding:8px 12px" rowspan="2">Umumiy tanlanma</td>
            <td style="padding:8px 12px;color:var(--teal)">Tajriba</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.exp_high)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.exp_mid)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.exp_low)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.exp_total)}</td>
            <td style="padding:8px 12px;text-align:center;color:${Number(ov.p_value) > 0.05 ? '#1E40AF' : 'var(--clay)'}" rowspan="2">χ² = ${esc(ov.chi2)}<br><span style="font-size:12px;font-weight:400;color:var(--muted)">p = ${esc(ov.p_value)}, df = ${esc(ov.df)}</span></td>
          </tr>
          <tr style="background:#EBF5FF;font-weight:700;border-bottom:1.5px solid var(--line)">
            <td style="padding:8px 12px;color:var(--muted)">Nazorat</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_high)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_mid)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_low)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_total)}</td>
          </tr>`;
      }
      const allEq = d.rows.length > 0 && d.rows.every(r => Number(r.p_value) > 0.05);
      const concl = (ov && ov.conclusion) ? ov.conclusion : (allEq
        ? "Barcha OTMlarda p > 0.05 bo'lib, Pearson Chi-Square mezoni bo'yicha tajriba va nazorat guruhlarining boshlang'ich tengligi isbotlangan."
        : "Ayrim OTMlarda p ≤ 0.05 — boshlang'ich farq mavjud, natijalarni ehtiyotkor talqin qiling.");
      html += `</tbody></table></div>
        <p style="margin-top:10px;font-size:12.5px;color:var(--muted);font-style:italic">Xulosa: ${esc(concl)}</p>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_6') {
      const d = researchTablesData.table_4_6;
      if (!d) { researchTableMissing(container, '4.6-jadval'); return; }
      const hasD = (d.skills || []).some(sk => sk.cohens_d !== undefined && sk.cohens_d !== null);
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Nutqiy faoliyat turi</th>
                <th style="padding:8px 12px">Guruh</th>
                <th style="padding:8px 12px;text-align:center">Boshida</th>
                <th style="padding:8px 12px;text-align:center">Yakunida</th>
                <th style="padding:8px 12px;text-align:center">O'sish sur'ati</th>
                <th style="padding:8px 12px;text-align:center">t-kriteriy</th>
                <th style="padding:8px 12px;text-align:center">Ahamiyatlilik</th>
                ${hasD ? `<th style="padding:8px 12px;text-align:center">Cohen's d</th>` : ''}
              </tr>
            </thead>
            <tbody>`;
      d.skills.forEach(sk => {
        html += `
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:8px 12px;font-weight:700" rowspan="2">${esc(sk.skill_name)}</td>
            <td style="padding:8px 12px;color:var(--teal);font-weight:600">Tajriba</td>
            <td style="padding:8px 12px;text-align:center">${esc(sk.exp_pre)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:var(--ink)">${esc(sk.exp_post)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:#16A34A">${esc(sk.exp_growth)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700" rowspan="2">${esc(sk.t_stat)}</td>
            <td style="padding:8px 12px;text-align:center;color:var(--teal);font-weight:600" rowspan="2">${esc(sk.p_val)}</td>
            ${hasD ? `<td style="padding:8px 12px;text-align:center;font-weight:700;color:#8B5CF6" rowspan="2">d = ${esc(sk.cohens_d == null ? '—' : sk.cohens_d)}<br><span style="font-size:11.5px;font-weight:400;color:var(--muted)">${esc(sk.cohens_d == null ? '' : effectLabel(sk.cohens_d))}</span></td>` : ''}
          </tr>
          <tr style="border-bottom:1.5px solid var(--line);background:var(--surface-2)">
            <td style="padding:8px 12px;color:var(--muted)">Nazorat</td>
            <td style="padding:8px 12px;text-align:center">${esc(sk.ctrl_pre)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(sk.ctrl_post)}</td>
            <td style="padding:8px 12px;text-align:center;color:var(--muted)">${esc(sk.ctrl_growth)}</td>
          </tr>`;
      });
      html += `</tbody></table></div>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_7') {
      const d = researchTablesData.table_4_7;
      if (!d) { researchTableMissing(container, '4.7-jadval'); return; }
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Metakognitiv komponent</th>
                <th style="padding:8px 12px">Guruh</th>
                <th style="padding:8px 12px;text-align:center">Boshida</th>
                <th style="padding:8px 12px;text-align:center">Yakunida</th>
                <th style="padding:8px 12px;text-align:center">O'sish</th>
                <th style="padding:8px 12px;text-align:center">Cohen's d</th>
                <th style="padding:8px 12px">Effekt darajasi</th>
              </tr>
            </thead>
            <tbody>`;
      d.components.forEach(c => {
        html += `
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:8px 12px;font-weight:600" rowspan="2">${esc(c.component)}</td>
            <td style="padding:8px 12px;color:var(--teal);font-weight:600">Tajriba</td>
            <td style="padding:8px 12px;text-align:center">${esc(c.exp_pre)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700">${esc(c.exp_post)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:#16A34A">${esc(c.exp_growth)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:var(--teal)" rowspan="2">d = ${esc(c.cohens_d)}</td>
            <td style="padding:8px 12px;font-size:12.5px" rowspan="2">${esc(c.effect_level)}</td>
          </tr>
          <tr style="border-bottom:1.5px solid var(--line);background:var(--surface-2)">
            <td style="padding:8px 12px;color:var(--muted)">Nazorat</td>
            <td style="padding:8px 12px;text-align:center">${esc(c.ctrl_pre)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(c.ctrl_post)}</td>
            <td style="padding:8px 12px;text-align:center;color:var(--muted)">${esc(c.ctrl_growth)}</td>
          </tr>`;
      });
      html += `</tbody></table></div>
        <p style="margin-top:10px;font-size:13px;font-weight:600;color:var(--teal)">O'rtacha umumiy Cohen's d = ${esc(d.average_d)} (${esc(effectLabel(d.average_d))})</p>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_8') {
      const d = researchTablesData.table_4_8;
      if (!d) { researchTableMissing(container, '4.8-jadval'); return; }
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Oliy ta'lim muassasasi</th>
                <th style="padding:8px 12px;text-align:center">Tajriba (K_taj)</th>
                <th style="padding:8px 12px;text-align:center">Nazorat (K_naz)</th>
                <th style="padding:8px 12px;text-align:center">Samaradorlik (K_s)</th>
                <th style="padding:8px 12px;text-align:center">Ustunlik (%)</th>
              </tr>
            </thead>
            <tbody>`;
      d.rows.forEach(r => {
        html += `
          <tr style="border-bottom:1px solid var(--line);height:40px">
            <td style="padding:8px 12px;font-weight:600">${esc(r.institution)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.exp_k)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_k)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:var(--teal)">K = ${esc(r.ratio_k)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:#16A34A">${esc(r.diff_percent)}</td>
          </tr>`;
      });
      html += `
          <tr style="background:#EBF5FF;font-weight:700;height:42px">
            <td style="padding:8px 12px">Umumiy o'rtacha ko'rsatkich</td>
            <td style="padding:8px 12px;text-align:center">${esc(d.overall.exp_k)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(d.overall.ctrl_k)}</td>
            <td style="padding:8px 12px;text-align:center;font-size:15px;color:#1E40AF">K_s = ${esc(d.overall.ratio_k)}</td>
            <td style="padding:8px 12px;text-align:center;color:#16A34A">${esc(d.overall.diff_percent)}</td>
          </tr>
        </tbody></table></div>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_9') {
      const d = researchTablesData.table_4_9;
      if (!d) { researchTableMissing(container, '4.9-jadval'); return; }
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Ko'rsatkichlar guruhi</th>
                <th style="padding:8px 12px;text-align:center">Hisoblangan qiymat</th>
                <th style="padding:8px 12px;text-align:center">Kriteriy qiymati</th>
                <th style="padding:8px 12px;text-align:center">Effekt hajmi / Farq</th>
                <th style="padding:8px 12px">Ilmiy-pedagogik xulosa</th>
              </tr>
            </thead>
            <tbody>`;
      d.indicators.forEach(ind => {
        html += `
          <tr style="border-bottom:1px solid var(--line);height:44px">
            <td style="padding:8px 12px;font-weight:600">${esc(ind.group)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:var(--teal)">${esc(ind.calculated)}</td>
            <td style="padding:8px 12px;text-align:center;color:var(--muted);font-size:12.5px">${esc(ind.table_crit)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700">${esc(ind.effect_size)}</td>
            <td style="padding:8px 12px;font-size:13px">${esc(ind.conclusion)}</td>
          </tr>`;
      });
      html += `</tbody></table></div>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_3') {
      // 4.3-jadval: baholash mezonlari va shkalasi (level_scale)
      const d = researchTablesData.level_scale;
      if (!d) { researchTableMissing(container, '4.3-jadval'); return; }
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Daraja</th>
                <th style="padding:8px 12px;text-align:center">Ball oralig'i</th>
                <th style="padding:8px 12px">Kommunikativ mezon</th>
                <th style="padding:8px 12px">Metakognitiv mezon</th>
              </tr>
            </thead>
            <tbody>`;
      (d.rows || []).forEach(r => {
        html += `
          <tr style="border-bottom:1px solid var(--line);height:40px">
            <td style="padding:8px 12px;font-weight:700;color:var(--teal)">${esc(r.level)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:600;white-space:nowrap">${esc(r.range)}</td>
            <td style="padding:8px 12px">${esc(r.communicative)}</td>
            <td style="padding:8px 12px">${esc(r.metacognitive)}</td>
          </tr>`;
      });
      html += `</tbody></table></div>
        <p style="margin-top:10px;font-size:12.5px;color:var(--muted);font-style:italic">Shkala 4.4-jadvaldagi daraja taqsimoti (Yuqori / O'rta / Quyi) va Bespalko koeffitsiyenti uchun asos bo'ladi.</p>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_5') {
      // 4.5-jadval: har guruh ichidagi pre → post dinamika (bog'langan t-mezon)
      const d = researchTablesData.table_4_5;
      if (!d) { researchTableMissing(container, '4.5-jadval'); return; }
      const hasN = (d.rows || []).some(r => r.exp_n !== undefined);
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">OTM</th>
                <th style="padding:8px 12px">Guruh</th>
                ${hasN ? `<th style="padding:8px 12px;text-align:center">n (pre+post)</th>` : ''}
                <th style="padding:8px 12px;text-align:center">Boshida</th>
                <th style="padding:8px 12px;text-align:center">Yakunida</th>
                <th style="padding:8px 12px;text-align:center">O'sish</th>
                <th style="padding:8px 12px;text-align:center">t (bog'langan)</th>
              </tr>
            </thead>
            <tbody>`;
      (d.rows || []).forEach(r => {
        html += `
          <tr style="border-bottom:1px solid var(--line)">
            <td style="padding:8px 12px;font-weight:600" rowspan="2">${esc(r.institution)}</td>
            <td style="padding:8px 12px;color:var(--teal);font-weight:600">Tajriba</td>
            ${hasN ? `<td style="padding:8px 12px;text-align:center">${esc(r.exp_n == null ? '—' : r.exp_n)}</td>` : ''}
            <td style="padding:8px 12px;text-align:center">${esc(r.exp_pre)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700">${esc(r.exp_post)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:#16A34A">${esc(r.exp_growth)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700">${esc(r.exp_t)}</td>
          </tr>
          <tr style="border-bottom:1.5px solid var(--line);background:var(--surface-2)">
            <td style="padding:8px 12px;color:var(--muted);font-weight:600">Nazorat</td>
            ${hasN ? `<td style="padding:8px 12px;text-align:center">${esc(r.ctrl_n == null ? '—' : r.ctrl_n)}</td>` : ''}
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_pre)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_post)}</td>
            <td style="padding:8px 12px;text-align:center;color:var(--muted)">${esc(r.ctrl_growth)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(r.ctrl_t)}</td>
          </tr>`;
      });
      const ov = d.overall;
      if (ov) {
        html += `
          <tr style="background:#EBF5FF;font-weight:700">
            <td style="padding:8px 12px" rowspan="2">Umumiy</td>
            <td style="padding:8px 12px;color:var(--teal)">Tajriba</td>
            ${hasN ? `<td style="padding:8px 12px"></td>` : ''}
            <td style="padding:8px 12px;text-align:center">${esc(ov.exp_pre)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.exp_post)}</td>
            <td style="padding:8px 12px;text-align:center;color:#16A34A">${esc(ov.exp_growth)}</td>
            <td style="padding:8px 12px;text-align:center">t = ${esc(ov.exp_t)}${ov.p_value ? `<br><span style="font-size:12px;font-weight:400;color:var(--muted)">p ${esc(ov.p_value)}</span>` : ''}</td>
          </tr>
          <tr style="background:#EBF5FF;font-weight:700">
            <td style="padding:8px 12px;color:var(--muted)">Nazorat</td>
            ${hasN ? `<td style="padding:8px 12px"></td>` : ''}
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_pre)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_post)}</td>
            <td style="padding:8px 12px;text-align:center">${esc(ov.ctrl_growth)}</td>
            <td style="padding:8px 12px;text-align:center">t = ${esc(ov.ctrl_t)}${ov.ctrl_p ? `<br><span style="font-size:12px;font-weight:400;color:var(--muted)">p ${esc(ov.ctrl_p)}</span>` : ''}</td>
          </tr>`;
      }
      html += `</tbody></table></div>`;
      container.innerHTML = html;
    } else if (activeResearchTab === 'tab_4_10') {
      // 4.10-jadval: nazariy kutilma va tajriba natijasi muvofiqligi
      let d = researchTablesData.table_4_10;
      let fallbackNote = '';
      if (!d && researchTablesData.table_4_6 && Array.isArray(researchTablesData.table_4_6.skills)) {
        // Dissertatsiya to'plamida 4.10 alohida kelmaydi — 4.6/4.7 o'sish ko'rsatkichlaridan tuziladi
        const EXPECT = {
          "Og'zaki nutq": "Dialog tizimlari hisobiga sezilarli o'sish",
          "Yozma nutq": "Izohli qaytar aloqa hisobiga o'rtacha o'sish",
          "O'qish": "Materialni darajaga moslashtirish hisobiga o'sish",
          "Tinglab tushunish": "Sur'at va variantlarni tabaqalashtirish hisobiga o'sish",
        };
        const rows = researchTablesData.table_4_6.skills.map(sk => {
          const name = Object.keys(EXPECT).find(k => String(sk.skill_name || '').indexOf(k) === 0) || sk.skill_name;
          const ok = typeof sk.exp_growth === 'string' && sk.exp_growth.startsWith('+') && sk.exp_growth !== '+0.0%';
          return { indicator: name, expectation: EXPECT[name] || "O'sish kutiladi", result: sk.exp_growth, match: ok ? 'Muvofiq' : 'Tekshirilmoqda' };
        });
        const t47 = researchTablesData.table_4_7;
        if (t47 && Array.isArray(t47.components)) {
          const meta = t47.components.filter(c => !/tashvish|anxiety/i.test(c.component || ''));
          if (meta.length) {
            const nums = meta.map(c => parseFloat(String(c.exp_growth || '').replace('%', '').replace('+', ''))).filter(x => !isNaN(x));
            const avg = nums.length ? (nums.reduce((a, b) => a + b, 0) / nums.length) : null;
            rows.push({ indicator: 'Metakognitiv ko\'rsatkich', expectation: 'Refleksiv bosqich hisobiga yuqori o\'sish', result: avg == null ? '—' : ((avg >= 0 ? '+' : '') + avg.toFixed(1) + '%'), match: avg != null && avg > 0 ? 'Muvofiq' : 'Tekshirilmoqda' });
          }
          const anx = t47.components.find(c => /tashvish|anxiety/i.test(c.component || ''));
          if (anx) rows.push({ indicator: 'Tashvish darajasi', expectation: 'Mashq muhitidagi xavfsizlik hisobiga pasayish', result: anx.exp_growth, match: String(anx.exp_growth || '').startsWith('-') ? 'Muvofiq' : 'Tekshirilmoqda' });
        }
        d = { title: '4.10-jadval. Nazariy kutilma va tajriba natijasining muvofiqligi', rows };
        fallbackNote = "Dissertatsiya to'plamida 4.10-jadval 4.6 va 4.7 jadvallarning o'sish ko'rsatkichlaridan tuzildi.";
      }
      if (!d) { researchTableMissing(container, '4.10-jadval'); return; }
      let html = `
        <h4 style="margin:0 0 12px;font-size:15px;color:var(--ink);font-weight:700">${esc(d.title)}</h4>
        <div style="overflow-x:auto">
          <table style="width:100%;font-size:13.5px;border-collapse:collapse;border:1px solid var(--line)">
            <thead>
              <tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink);height:38px;text-align:left">
                <th style="padding:8px 12px">Ko'rsatkich</th>
                <th style="padding:8px 12px">Nazariy kutilma</th>
                <th style="padding:8px 12px;text-align:center">Tajriba natijasi</th>
                <th style="padding:8px 12px;text-align:center">Muvofiqlik</th>
              </tr>
            </thead>
            <tbody>`;
      (d.rows || []).forEach(r => {
        const ok = r.match === 'Muvofiq';
        html += `
          <tr style="border-bottom:1px solid var(--line);height:40px">
            <td style="padding:8px 12px;font-weight:600">${esc(r.indicator)}</td>
            <td style="padding:8px 12px;color:var(--ink-2)">${esc(r.expectation)}</td>
            <td style="padding:8px 12px;text-align:center;font-weight:700;color:${ok ? '#16A34A' : 'var(--amber)'}">${esc(r.result)}</td>
            <td style="padding:8px 12px;text-align:center"><span class="chip ${ok ? 'none' : 'part'}" style="font-weight:600">${ok ? '✔ ' : '⏳ '}${esc(r.match)}</span></td>
          </tr>`;
      });
      html += `</tbody></table></div>` + (fallbackNote ? `<p style="margin-top:10px;font-size:12.5px;color:var(--muted);font-style:italic">${esc(fallbackNote)}</p>` : '');
      container.innerHTML = html;
    }
  }

  // ==========================================
  // 4b. JONLI REJIM: baholash natijalarini kiritish, ro'yxat, jarayon ko'rsatkichlari
  // ==========================================
  function fillResearchSkillSelect(skills) {
    const sel = document.getElementById('rmSkill');
    if (!sel) return;
    const cur = sel.value;
    const list = (skills && skills.length) ? skills : ['listening', 'reading', 'speaking', 'writing'];
    sel.innerHTML = list.map(s => `<option value="${esc(s)}">${esc(s)}</option>`).join('');
    if (list.includes(cur)) sel.value = cur;
    else if (list.includes('writing')) sel.value = 'writing';
  }

  window.researchToggleCsvSample = function() {
    const el = document.getElementById('researchCsvSample');
    if (el) el.style.display = (el.style.display === 'none' || !el.style.display) ? 'block' : 'none';
  };

  function importResultHtml(res) {
    const errs = (res.errors || []);
    let html = `<div style="color:${res.error_count ? 'var(--amber)' : '#16A34A'};font-weight:600">✔ Saqlandi: ${esc(res.saved || 0)}${res.received != null ? ' / ' + esc(res.received) : ''} · Xatolar: ${esc(res.error_count || 0)}</div>`;
    if (errs.length) html += `<ul style="margin:4px 0 0;padding-left:18px;color:var(--clay);font-size:12px;max-height:140px;overflow-y:auto">${errs.map(e => `<li>${esc(e)}</li>`).join('')}</ul>`;
    return html;
  }

  window.researchImportFile = async function() {
    const inp = document.getElementById('researchImportFile');
    const out = document.getElementById('researchImportResult');
    if (!inp || !inp.files || !inp.files[0]) { rToast('Avval CSV yoki JSON faylni tanlang.', 'error'); return; }
    const fd = new FormData();
    fd.append('file', inp.files[0]);
    if (out) out.innerHTML = '<span style="color:var(--muted)">Yuklanmoqda...</span>';
    try {
      const res = await researchRequest('/research/live/assessments/import', { method: 'POST', body: fd });
      if (out) out.innerHTML = importResultHtml(res);
      rToast('Import yakunlandi: ' + (res.saved || 0) + ' ta yozuv saqlandi.', res.error_count ? 'info' : 'success');
      inp.value = '';
      await loadLiveResearch();
    } catch (e) {
      if (out) out.innerHTML = `<span style="color:var(--clay)">Xatolik: ${esc(e.message)}</span>`;
      rToast(e.message, 'error');
    }
  };

  window.researchSubmitManual = async function() {
    const out = document.getElementById('researchManualResult');
    const g = (id) => { const el = document.getElementById(id); return el ? el.value : ''; };
    const email = g('rmEmail').trim();
    const score = parseFloat(g('rmScore'));
    const max = parseFloat(g('rmMax')) || 100;
    if (!email || isNaN(score)) { rToast('Email va ballni kiriting.', 'error'); return; }
    if (score > max) { rToast('Ball maksimumdan katta bo\'lmasin.', 'error'); return; }
    const item = { email, assessment_type: g('rmType') || 'pre', skill: g('rmSkill') || 'writing', score, max_score: max };
    if (out) out.innerHTML = '<span style="color:var(--muted)">Saqlanmoqda...</span>';
    try {
      const res = await researchRequest('/research/live/assessments', { method: 'POST', body: { items: [item] } });
      if (out) out.innerHTML = importResultHtml(res);
      if (res.saved) {
        rToast('Baho saqlandi.', 'success');
        const sc = document.getElementById('rmScore'); if (sc) sc.value = '';
        await loadLiveResearch();
      } else {
        rToast((res.errors && res.errors[0]) || 'Saqlanmadi.', 'error');
      }
    } catch (e) {
      if (out) out.innerHTML = `<span style="color:var(--clay)">Xatolik: ${esc(e.message)}</span>`;
      rToast(e.message, 'error');
    }
  };

  window.researchReloadAssessments = async function() {
    const box = document.getElementById('researchAssessmentsList');
    if (!box) return;
    if (!canUseLiveResearch()) { box.innerHTML = ''; return; }
    const canDelete = ['researcher', 'admin'].includes(researchRole());
    try {
      const res = await researchRequest('/research/live/assessments?limit=50');
      const items = res.items || [];
      if (!items.length) { box.innerHTML = '<div style="color:var(--muted);font-size:12.5px;padding:10px">Hali baholar kiritilmagan.</div>'; return; }
      const th = 'padding:7px 10px;font-size:12px;white-space:nowrap;text-align:left';
      const td = 'padding:7px 10px;font-size:12.5px;white-space:nowrap';
      let html = `<table style="width:100%;border-collapse:collapse;min-width:720px"><thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">
        <th style="${th}">Sana</th><th style="${th}">Talaba</th><th style="${th}">Guruh</th><th style="${th}">Tur</th><th style="${th}">Ko'nikma</th><th style="${th};text-align:center">Ball</th>${canDelete ? `<th style="${th}"></th>` : ''}</tr></thead><tbody>`;
      items.forEach(it => {
        const armTxt = it.arm === 'experimental' ? 'Tajriba' : (it.arm === 'control' ? 'Nazorat' : '');
        html += `<tr style="border-bottom:1px solid var(--line)">
          <td style="${td}">${esc(it.administered_at)}</td>
          <td style="${td}"><b>${esc(it.student)}</b><br><span style="font-size:11px;color:var(--muted)">${esc(it.email)}</span></td>
          <td style="${td}">${esc(it.group || '—')}${armTxt ? ` <span class="chip ${it.arm === 'experimental' ? 'none' : 'part'}" style="padding:1px 7px">${armTxt}</span>` : ''}</td>
          <td style="${td};font-weight:600">${esc(it.assessment_type)}</td>
          <td style="${td}">${esc(it.skill)}</td>
          <td style="${td};text-align:center;font-weight:700">${esc(it.score)} / ${esc(it.max_score)}</td>
          ${canDelete ? `<td style="${td}"><button onclick="window.researchDeleteAssessment(${rArg(it.id)})" title="O'chirish" style="cursor:pointer;border:1px solid var(--line);background:var(--surface-2);color:var(--clay);border-radius:6px;padding:3px 8px;font-size:12px">🗑</button></td>` : ''}
        </tr>`;
      });
      html += '</tbody></table>';
      box.innerHTML = html;
    } catch (e) {
      box.innerHTML = `<div style="color:var(--clay);font-size:12.5px;padding:10px">Ro'yxatni yuklab bo'lmadi: ${esc(e.message)}</div>`;
    }
  };

  window.researchDeleteAssessment = async function(id) {
    if (!id) return;
    try {
      await researchRequest('/research/live/assessments/' + encodeURIComponent(id), { method: 'DELETE' });
      rToast('Baho o\'chirildi.', 'success');
      await loadLiveResearch();
    } catch (e) {
      rToast(e.message, 'error');
    }
  };

  // ---------- 4.1: O'lchov vositalarining ishonchliligi (Cronbach α, baholovchilar mosligi) ----------
  const REL_INSTRUMENTS = { flcas: 'FLCAS (tashvish)', mslq: 'MSLQ (metakognitiv)', cognitive: 'Kognitiv profil', sill: 'SILL (strategiyalar)' };
  const REL_DIMS = {
    anxiety: 'Tashvish', planning: 'Rejalashtirish', monitoring: 'Kuzatish', evaluation: 'Baholash', regulation: 'Boshqarish',
    load_capacity: "Yuklama sig'imi", pace: "Sur'at", autonomy: 'Mustaqillik', motivation: 'Motivatsiya',
    memory: 'Xotira', cognitive: 'Kognitiv', compensation: 'Kompensatsiya', metacognitive: 'Metakognitiv', affective: 'Affektiv', social: 'Ijtimoiy',
  };
  const RATER_ROWS = [['content', 'Mazmun'], ['grammar', 'Grammatika'], ['lexis', 'Leksika'], ['coherence', "Bog'liqlik"], ['overall', 'Umumiy (barcha mezonlar)'], ['microteaching_peer_vs_teacher', "Mikroo'qitish: tengdoshlar vs o'qituvchi"]];

  function alphaCell(a) {
    if (a === null || a === undefined) return '<span style="color:var(--muted)">—</span>';
    const col = a >= 0.8 ? 'var(--teal)' : (a >= 0.7 ? 'var(--amber)' : 'var(--clay)');
    return '<b style="color:' + col + '">' + esc(Number(a).toFixed(3)) + '</b>';
  }

  async function loadReliability() {
    const box = document.getElementById('researchReliability');
    if (!box) return;
    const th = 'padding:7px 10px;font-size:12px;white-space:nowrap;text-align:center';
    const td = 'padding:7px 10px;font-size:12.5px;text-align:center';
    const f = (v) => (v === null || v === undefined) ? '—' : esc(v);
    const pct = (v) => (typeof v === 'number') ? esc(Math.round(v * 100)) + '%' : '—';
    const num = (v) => (typeof v === 'number') ? esc(v.toFixed(2)) : '—';
    try {
      const res = await researchRequest('/research/live/reliability');
      const cr = res.cronbach || {};
      let html = '<div style="font-size:12.5px;font-weight:700;margin-bottom:6px">a) Ichki izchillik — Cronbach α</div>'
        + '<div style="overflow-x:auto;margin-bottom:14px"><table style="width:100%;border-collapse:collapse;min-width:640px"><thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">'
        + '<th style="' + th + ';text-align:left">Vosita</th><th style="' + th + ';text-align:left">O\'lchov</th><th style="' + th + '">α</th><th style="' + th + '">Respondentlar</th><th style="' + th + '">Bandlar</th><th style="' + th + ';text-align:left">Talqin</th></tr></thead><tbody>';
      Object.keys(cr).forEach(inst => {
        const block = cr[inst] || {};
        const ov = block.overall || {};
        html += '<tr style="border-bottom:1px solid var(--line);background:var(--surface-2)"><td style="' + td + ';text-align:left;font-weight:700">' + esc(REL_INSTRUMENTS[inst] || inst) + '</td><td style="' + td + ';text-align:left;font-weight:600">Umumiy</td>'
          + '<td style="' + td + '">' + alphaCell(ov.alpha) + '</td><td style="' + td + '">' + f(ov.n_respondents) + '</td><td style="' + td + '">' + f(ov.n_items) + '</td><td style="' + td + ';text-align:left;color:var(--muted)">' + f(ov.label) + '</td></tr>';
        const dims = block.dimensions || {};
        Object.keys(dims).forEach(dk => {
          const d = dims[dk] || {};
          html += '<tr style="border-bottom:1px solid var(--line)"><td style="' + td + '"></td><td style="' + td + ';text-align:left;padding-left:22px">' + esc(REL_DIMS[dk] || dk) + '</td>'
            + '<td style="' + td + '">' + alphaCell(d.alpha) + '</td><td style="' + td + '">' + f(d.n_respondents) + '</td><td style="' + td + '">' + f(d.n_items) + '</td><td style="' + td + ';text-align:left;color:var(--muted)">' + f(d.label) + '</td></tr>';
        });
      });
      html += '</tbody></table></div>';
      const ir = res.inter_rater || {};
      html += '<div style="font-size:12.5px;font-weight:700;margin-bottom:6px">b) Baholovchilar mosligi — tizim rubrikasi vs o\'qituvchi (ikki marta baholangan yozuvlar: <b>' + esc(ir.records_double_rated == null ? 0 : ir.records_double_rated) + '</b>)</div>'
        + '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;min-width:640px"><thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">'
        + '<th style="' + th + ';text-align:left">Mezon</th><th style="' + th + '">n</th><th style="' + th + '">Aniq moslik</th><th style="' + th + '">±1 moslik</th><th style="' + th + '">Pearson r</th><th style="' + th + '">κ (vaznli)</th><th style="' + th + ';text-align:left">Talqin</th></tr></thead><tbody>';
      RATER_ROWS.forEach(([k, label]) => {
        const a = ir[k] || {};
        const kap = typeof a.kappa === 'number' ? a.kappa : null;
        const col = kap === null ? 'var(--muted)' : (kap >= 0.6 ? 'var(--teal)' : (kap >= 0.4 ? 'var(--amber)' : 'var(--clay)'));
        html += '<tr style="border-bottom:1px solid var(--line)' + (k === 'overall' ? ';background:var(--surface-2);font-weight:700' : '') + '"><td style="' + td + ';text-align:left">' + esc(label) + '</td>'
          + '<td style="' + td + '">' + esc(a.n == null ? 0 : a.n) + '</td><td style="' + td + '">' + pct(a.exact) + '</td><td style="' + td + '">' + pct(a.adjacent) + '</td><td style="' + td + '">' + num(a.r) + '</td>'
          + '<td style="' + td + '"><b style="color:' + col + '">' + num(a.kappa) + '</b></td><td style="' + td + ';text-align:left;color:var(--muted)">' + f(a.label) + '</td></tr>';
      });
      html += '</tbody></table></div>';
      if (res.note) html += '<div style="font-size:11.5px;color:var(--muted);margin-top:8px">' + esc(res.note) + '</div>';
      box.innerHTML = html;
    } catch (e) {
      box.innerHTML = researchNotice('Ishonchlilik ko\'rsatkichlarini yuklab bo\'lmadi: ' + esc(e.message), 'error');
    }
  }

  // ---------- SILL strategiyalari (Oxford): guruhlar × tajriba/nazorat pre/post ----------
  async function loadSillSummary() {
    const box = document.getElementById('researchSill');
    if (!box) return;
    const th = 'padding:7px 10px;font-size:12px;white-space:nowrap;text-align:center';
    const td = 'padding:7px 10px;font-size:12.5px;text-align:center';
    const num = (v) => (typeof v === 'number') ? esc(v.toFixed(2)) : '—';
    const growth = (g) => {
      if (g === null || g === undefined || g === '—' || g === '') return '<span style="color:var(--muted)">—</span>';
      const n = Number(String(g).replace('%', '').replace('+', ''));
      const col = isNaN(n) ? 'var(--ink)' : (n > 0 ? '#16A34A' : (n < 0 ? 'var(--clay)' : 'var(--muted)'));
      return '<b style="color:' + col + '">' + esc(g) + '</b>';
    };
    try {
      const res = await researchRequest('/research/live/sill');
      const groups = res.groups || {};
      const meta = res.meta || {};
      const keys = Object.keys(groups);
      if (!keys.length) { box.innerHTML = '<div style="color:var(--muted);font-size:12.5px;padding:10px">SILL natijalari hali yo\'q.</div>'; return; }
      let html = '<table style="width:100%;border-collapse:collapse;min-width:760px"><thead>'
        + '<tr style="background:var(--surface-2)"><th style="' + th + ';text-align:left" rowspan="2">Strategiya guruhi</th><th colspan="3" style="' + th + ';border-bottom:1px solid var(--line)">Tajriba guruhi</th><th colspan="3" style="' + th + ';border-bottom:1px solid var(--line)">Nazorat guruhi</th></tr>'
        + '<tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)"><th style="' + th + '">Pre (n)</th><th style="' + th + '">Post (n)</th><th style="' + th + '">O\'sish</th><th style="' + th + '">Pre (n)</th><th style="' + th + '">Post (n)</th><th style="' + th + '">O\'sish</th></tr></thead><tbody>';
      keys.forEach(k => {
        const m = meta[k] || {};
        const e = (groups[k] || {}).experimental || {};
        const c = (groups[k] || {}).control || {};
        const cell = (v, n) => num(v) + (n ? ' <span style="font-size:11px;color:var(--muted)">(' + esc(n) + ')</span>' : '');
        html += '<tr style="border-bottom:1px solid var(--line)"><td style="' + td + ';text-align:left"><b>' + esc(m.name || k) + '</b>' + (m.desc ? '<div style="font-size:11px;color:var(--muted)">' + esc(m.desc) + '</div>' : '') + '</td>'
          + '<td style="' + td + '">' + cell(e.pre, e.n_pre) + '</td><td style="' + td + ';font-weight:700">' + cell(e.post, e.n_post) + '</td><td style="' + td + '">' + growth(e.growth) + '</td>'
          + '<td style="' + td + '">' + cell(c.pre, c.n_pre) + '</td><td style="' + td + ';font-weight:700">' + cell(c.post, c.n_post) + '</td><td style="' + td + '">' + growth(c.growth) + '</td></tr>';
      });
      html += '</tbody></table><div style="font-size:11.5px;color:var(--muted);margin-top:8px">Qiymatlar 1–5 shkalada (Oxford, 1990: 1.0–2.4 past, 2.5–3.4 o\'rta, 3.5–5.0 yuqori qo\'llanish); n — javob bergan talabalar soni.</div>';
      box.innerHTML = html;
    } catch (e) {
      box.innerHTML = researchNotice('SILL natijalarini yuklab bo\'lmadi: ' + esc(e.message), 'error');
    }
  }

  // ---------- Admin: ma'lumotlarni saqlash muddati (retention) ----------
  let retentionStatus = null;
  function retentionHtml(st, extra) {
    const th = 'padding:6px 10px;font-size:12px;white-space:nowrap;text-align:left';
    const td = 'padding:6px 10px;font-size:12.5px';
    const preview = st.stale_preview || [];
    let html = '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;font-size:12.5px">'
      + '<span style="background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:4px 10px">Saqlash muddati: <b>' + esc(st.retention_days) + ' kun</b></span>'
      + '<span style="background:var(--surface-2);border:1px solid var(--line);border-radius:8px;padding:4px 10px">Chegara sanasi: <b>' + esc(st.cutoff || '—') + '</b></span>'
      + '<span style="background:' + (st.stale_accounts > 0 ? 'var(--amber-soft)' : 'var(--teal-soft)') + ';border:1px solid var(--line);border-radius:8px;padding:4px 10px">Muddati o\'tgan hisoblar: <b>' + esc(st.stale_accounts == null ? 0 : st.stale_accounts) + '</b></span>'
      + '</div>'
      + '<div style="font-size:12.5px;color:var(--ink-2);line-height:1.55;margin-bottom:10px"><b>Siyosat:</b> ' + esc(st.policy || '') + '</div>';
    if (preview.length) {
      html += '<div style="overflow-x:auto;margin-bottom:10px"><table style="width:100%;border-collapse:collapse;min-width:420px"><thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)"><th style="' + th + '">ID</th><th style="' + th + '">Email</th><th style="' + th + '">Oxirgi faollik</th></tr></thead><tbody>'
        + preview.map(u => '<tr style="border-bottom:1px solid var(--line)"><td style="' + td + ';font-family:var(--mono);font-size:11.5px">' + esc(String(u.id || '').slice(0, 8)) + '…</td><td style="' + td + '">' + esc(u.email) + '</td><td style="' + td + '">' + esc(u.last || '—') + '</td></tr>').join('')
        + '</tbody></table>' + (st.stale_accounts > preview.length ? '<div style="font-size:11.5px;color:var(--muted);margin-top:4px">Birinchi ' + esc(preview.length) + ' tasi ko\'rsatildi.</div>' : '') + '</div>';
    } else {
      html += '<div style="font-size:12.5px;color:var(--muted);padding:8px 10px;border:1px dashed var(--line);border-radius:8px;margin-bottom:10px">Muddati o\'tgan faol hisoblar yo\'q.</div>';
    }
    html += '<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">'
      + '<button class="btn-primary" style="padding:7px 12px;font-size:12.5px;background:var(--surface-2);color:var(--ink);border:1px solid var(--line)" onclick="window.researchRetentionDryRun && window.researchRetentionDryRun()">🧪 Dry-run (sinov hisob-kitobi)</button>'
      + '<input type="text" id="researchRetentionConfirm" placeholder="Tasdiqlash uchun TASDIQLAYMAN deb yozing" autocomplete="off" style="padding:7px 9px;border:1px solid var(--line);border-radius:7px;background:var(--surface);font-size:12.5px;min-width:260px">'
      + '<button class="btn-primary" style="padding:7px 12px;font-size:12.5px;background:var(--clay);border-color:var(--clay)" onclick="window.researchRetentionPurge && window.researchRetentionPurge()">🗑 Anonimlashtirish</button>'
      + '</div>'
      + '<div id="researchRetentionResult" style="margin-top:8px;font-size:12.5px">' + (extra || '') + '</div>';
    return html;
  }

  async function loadRetentionCard() {
    const card = document.getElementById('researchRetentionCard');
    const box = document.getElementById('researchRetention');
    if (!card || !box) return;
    if (researchRole() !== 'admin') { card.style.display = 'none'; return; }
    card.style.display = 'block';
    try {
      retentionStatus = await researchRequest('/admin/retention/status');
      box.innerHTML = retentionHtml(retentionStatus);
    } catch (e) {
      box.innerHTML = researchNotice('Retention holatini yuklab bo\'lmadi: ' + esc(e.message), 'error');
    }
  }

  window.researchRetentionDryRun = async function () {
    const out = document.getElementById('researchRetentionResult');
    if (out) out.innerHTML = '<span style="color:var(--muted)">Hisoblanmoqda...</span>';
    try {
      const res = await researchRequest('/admin/retention/purge?dry_run=true', { method: 'POST' });
      if (out) out.innerHTML = researchNotice('<b>Dry-run:</b> anonimlashtirishga tayyor hisoblar soni — <b>' + esc(res.count == null ? 0 : res.count) + '</b> (muddat ' + esc(res.retention_days) + ' kun). Hech narsa o\'zgartirilmadi.', 'warn');
    } catch (e) {
      if (out) out.innerHTML = researchNotice(esc(e.message), 'error');
      rToast(e.message, 'error');
    }
  };

  window.researchRetentionPurge = async function () {
    const inp = document.getElementById('researchRetentionConfirm');
    const out = document.getElementById('researchRetentionResult');
    if (!inp || inp.value.trim() !== 'TASDIQLAYMAN') {
      rToast('Tasdiqlash uchun maydonga aynan TASDIQLAYMAN deb yozing.', 'error');
      if (inp) { inp.focus(); inp.style.outline = '1.5px solid var(--clay)'; }
      return;
    }
    inp.style.outline = '';
    if (out) out.innerHTML = '<span style="color:var(--muted)">Anonimlashtirilmoqda...</span>';
    try {
      const res = await researchRequest('/admin/retention/purge?dry_run=false', { method: 'POST' });
      rToast('Anonimlashtirildi: ' + (res.count == null ? 0 : res.count) + ' ta hisob.', 'success');
      try { retentionStatus = await researchRequest('/admin/retention/status'); } catch (e2) { /* holat yangilanmasa ham natija ko'rsatiladi */ }
      const box = document.getElementById('researchRetention');
      if (box && retentionStatus) box.innerHTML = retentionHtml(retentionStatus, researchNotice('<b>Bajarildi:</b> ' + esc(res.count == null ? 0 : res.count) + ' ta hisob anonimlashtirildi (status: ' + esc(res.status) + ').', 'ok'));
      else if (out) out.innerHTML = researchNotice('<b>Bajarildi:</b> ' + esc(res.count == null ? 0 : res.count) + ' ta hisob anonimlashtirildi.', 'ok');
    } catch (e) {
      if (out) out.innerHTML = researchNotice(esc(e.message), 'error');
      rToast(e.message, 'error');
    }
  };

  async function loadProcessIndicators() {
    const box = document.getElementById('researchProcessIndicators');
    if (!box) return;
    try {
      const res = await researchRequest('/research/live/process-indicators');
      const by = res.by_arm || {};
      const arms = [['experimental', 'Tajriba'], ['control', 'Nazorat'], ['none', 'Qanotsiz']];
      const th = 'padding:7px 10px;font-size:12px;white-space:nowrap;text-align:center';
      const td = 'padding:7px 10px;font-size:12.5px;text-align:center';
      const f = (v) => (v === null || v === undefined) ? '—' : esc(v);
      let html = `<table style="width:100%;border-collapse:collapse;min-width:860px"><thead><tr style="background:var(--surface-2);border-bottom:1.5px solid var(--ink)">
        <th style="${th};text-align:left">Qanot</th><th style="${th}">Yozuvlar</th><th style="${th}">O'rt. ball</th><th style="${th}" title="Mustaqil bosqichdagi o'rtacha vaqt">Mustaqil (daq)</th>
        <th style="${th}" title="Mustaqil bosqichda qulflangan AI ga urinishlar">Yordam so'rovi</th><th style="${th}">O'z tekshiruvi</th><th style="${th}" title="O'z bahosi va tizim bahosi farqi">O'z bahosi farqi</th>
        <th style="${th}">Izoh qabul %</th><th style="${th};text-align:left">Takror L1 naqshlar</th></tr></thead><tbody>`;
      arms.forEach(([k, label]) => {
        const s = by[k] || { records: 0 };
        if (k === 'none' && !s.records) return;
        const pats = (s.recurring_l1_patterns || []);
        html += `<tr style="border-bottom:1px solid var(--line)">
          <td style="${td};text-align:left;font-weight:700;color:${k === 'experimental' ? 'var(--teal)' : 'var(--ink)'}">${esc(label)}</td>
          <td style="${td}">${f(s.records)}</td>
          <td style="${td};font-weight:700">${f(s.avg_score)}</td>
          <td style="${td}">${f(s.avg_independent_minutes)}</td>
          <td style="${td}">${f(s.avg_help_requests)}</td>
          <td style="${td}">${f(s.avg_self_checks)}</td>
          <td style="${td}">${f(s.avg_rating_gap)}</td>
          <td style="${td}">${typeof s.feedback_accept_rate === 'number' ? esc(Math.round(s.feedback_accept_rate * 100)) + '%' : '—'}</td>
          <td style="${td};text-align:left">${pats.length ? pats.map(p => `<span class="chip full" style="padding:1px 7px;margin:1px;display:inline-block">${esc(p[0])} ×${esc(p[1])}</span>`).join('') : '<span style="color:var(--muted)">—</span>'}</td>
        </tr>`;
      });
      html += `</tbody></table><p style="margin:8px 0 0;font-size:12px;color:var(--muted)">Jami mashg'ulot yozuvlari: <b>${esc(res.total_records || 0)}</b>.</p>`;
      box.innerHTML = html;
    } catch (e) {
      box.innerHTML = `<div style="color:var(--clay);font-size:12.5px;padding:10px">Jarayon ko'rsatkichlarini yuklab bo'lmadi: ${esc(e.message)}</div>`;
    }
  }

  // Eksport: Authorization sarlavhasi bilan fetch qilib, blob orqali yuklab olish
  async function downloadResearchExport(path, filename) {
    const toast = (msg, type) => { if (typeof window.showToast === 'function') window.showToast(msg, type); };
    try {
      const token = (window.STATE && STATE.token) ? STATE.token : (localStorage.getItem('tilora_token') || '');
      const res = await fetch(researchApiBase() + path, {
        headers: token ? { 'Authorization': 'Bearer ' + token } : {}
      });
      if (!res.ok) {
        if (res.status === 401) {
          toast('Eksport uchun tizimga kiring', 'error');
        } else {
          toast('Eksport muvaffaqiyatsiz (HTTP ' + res.status + ')', 'error');
        }
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      console.warn('Eksport xatoligi:', e);
      toast('Eksport muvaffaqiyatsiz', 'error');
    }
  }

  // Jonli rejimda ?source=live — eksport platformadagi haqiqiy ma'lumotlardan tuziladi
  window.downloadDocxExport = function() {
    downloadResearchExport('/research/export-docx' + researchSourceQuery(), 'TILORA_4-bob_jadvallari_' + researchSource + '.docx');
  };

  window.downloadExcelExport = function() {
    downloadResearchExport('/research/export-excel' + researchSourceQuery(), 'TILORA_4-bob_jadvallari_' + researchSource + '.xlsx');
  };

  window.downloadCsvExport = function() {
    downloadResearchExport('/research/export-csv' + researchSourceQuery(), 'TILORA_4-bob_jadvallari_' + researchSource + '.csv');
  };

  // ==========================================
  // 5. TO'RT NUTQIY KO'NIKMA (SKILLS) INTERAKTIVI
  // ==========================================
  let currentLessonSkill = 'writing';
  let mediaRecorder = null;
  let audioChunks = [];
  let recordingInterval = null;
  let recordingSeconds = 0;
  let speechRecognition = null;

  window.switchLessonSkill = function(skill) {
    currentLessonSkill = skill;
    document.querySelectorAll('.skill-tab-btn').forEach(btn => {
      if (btn.getAttribute('data-skill') === skill) {
        btn.classList.add('active');
        btn.style.background = 'var(--teal)';
        btn.style.color = '#fff';
      } else {
        btn.classList.remove('active');
        btn.style.background = 'var(--surface-2)';
        btn.style.color = 'var(--ink)';
      }
    });

    // Mashg'ulot sarlavhalari va ko'rinishini almashtirish
    const promptTitle = document.getElementById('lessonTaskPromptTitle');
    const promptDesc = document.getElementById('lessonTaskPromptDesc');
    const writingArea = document.getElementById('writingProductionBox');
    const speakingArea = document.getElementById('speakingProductionBox');
    const listeningArea = document.getElementById('listeningProductionBox');
    const readingArea = document.getElementById('readingProductionBox');

    if (writingArea) writingArea.style.display = (skill === 'writing') ? 'block' : 'none';
    if (speakingArea) speakingArea.style.display = (skill === 'speaking') ? 'block' : 'none';
    if (listeningArea) listeningArea.style.display = (skill === 'listening') ? 'block' : 'none';
    if (readingArea) readingArea.style.display = (skill === 'reading') ? 'block' : 'none';

    const isRu = (currentLang === 'ru');
    const isEn = (currentLang === 'en');

    if (skill === 'speaking') {
      if (promptTitle) promptTitle.textContent = isRu 
        ? "🎙️ Устная речь: решение педагогического кейса (Speaking Task)" 
        : (isEn ? "🎙️ Speaking Task: Pedagogical Case Solution" : "🎙️ Og'zaki nutq: Pedagogik keys yechimi (Speaking Task)");
      if (promptDesc) promptDesc.textContent = isRu 
        ? "Ситуация: Студенты на занятии пассивны. В роли преподавателя изложите методы их вовлечения в течение 1.5–2 минут на английском языке." 
        : (isEn ? "Situation: Students are passive during class. As an instructor, articulate your engagement strategies for 1.5–2 minutes in spoken English." : "Vaziyat: Talabalar darsda passiv bo'lib qoldi. O'qituvchi sifatida ularning darsga jalb qilish metodlarini 1.5–2 daqiqa davomida ingliz tilida nutq so'zlab bayon eting.");
    } else if (skill === 'listening') {
      if (promptTitle) promptTitle.textContent = isRu 
        ? "🎧 Аудирование: анализ профессиональной лекции (Listening Comprehension)" 
        : (isEn ? "🎧 Listening Comprehension: Professional Lecture Analysis" : "🎧 Tinglab tushunish: Kasbiy ma'ruza tahlili (Listening Comprehension)");
      if (promptDesc) promptDesc.textContent = isRu 
        ? "Прослушайте аудиофрагмент, выделите три основные методические рекомендации и напишите краткий аналитический комментарий." 
        : (isEn ? "Listen to the audio excerpt, identify the three key pedagogical recommendations, and write a brief analytical commentary." : "Audio parchasini tinglang va unda tilga olingan uchta asosiy metodik tavsiyani belgilang hamda qisqa izoh yozing.");
    } else if (skill === 'reading') {
      if (promptTitle) promptTitle.textContent = isRu 
        ? "📖 Чтение: анализ научно-методической статьи (Reading Task)" 
        : (isEn ? "📖 Reading Task: Research Article Analysis" : "📖 O'qish: Ilmiy-metodik maqola tahlili (Reading Task)");
      if (promptDesc) promptDesc.textContent = isRu 
        ? "Внимательно прочитайте текст, выделите основные тезисы и дайте аргументированные ответы на поставленные вопросы." 
        : (isEn ? "Carefully read the text, extract the core arguments, and provide reasoned answers to the questions." : "Matnni diqqat bilan o'qing, asosiy tezislarni ajrating va berilgan savollarga mustaqil javob qaytaring.");
    } else {
      if (promptTitle) promptTitle.textContent = isRu 
        ? "✍️ Письменная речь: анализ урока и критерии оценивания (Writing Task)" 
        : (isEn ? "✍️ Writing Task: Lesson Evaluation & Assessment Criteria" : "✍️ Yozma nutq: dars tahlili va baholash mezonlari (Writing Task)");
      if (promptDesc) promptDesc.textContent = isRu 
        ? "Какие критерии целесообразно использовать при оценивании письменной речи учащихся? Изложите свою позицию в объёме 150–180 слов в академическом стиле." 
        : (isEn ? "What criteria should be utilized to assess learners' written production? Present your reasoned argument in 150–180 words using academic language." : "O'quvchilarning yozma nutqini baholashda qanday mezonlardan foydalanish mumkin? O'z fikringizni 150–180 so'zda ilmiy-metodik bayon eting.");
    }
  };

  // Ovoz yozish (Speaking)
  window.toggleVoiceRecording = async function() {
    const btn = document.getElementById('btnRecordVoice');
    const timerEl = document.getElementById('recordTimer');
    const statusEl = document.getElementById('recordStatus');
    const audioPreview = document.getElementById('speakingAudioPreview');
    const isRu = (currentLang === 'ru');
    const isEn = (currentLang === 'en');

    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          const audioUrl = URL.createObjectURL(audioBlob);
          if (audioPreview) {
            audioPreview.src = audioUrl;
            audioPreview.style.display = 'block';
          }
          stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorder.start();
        recordingSeconds = 0;
        if (recordingInterval) clearInterval(recordingInterval);
        recordingInterval = setInterval(() => {
          recordingSeconds++;
          const m = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
          const s = String(recordingSeconds % 60).padStart(2, '0');
          if (timerEl) timerEl.textContent = `${m}:${s}`;
        }, 1000);

        if (btn) {
          btn.innerHTML = isRu ? "⏹️ Остановить и сохранить" : (isEn ? "⏹️ Stop & Save" : "⏹️ To'xtatish va saqlash");
          btn.style.background = "#DC2626";
          btn.style.color = "#fff";
        }
        if (statusEl) {
          statusEl.textContent = isRu 
            ? "🔴 Запись звука... Говорите бегло на английском языке." 
            : (isEn ? "🔴 Recording in progress... Speak fluently in English." : "🔴 Ovoz yozilmoqda... Ingliz tilida ravon gapiring.");
          statusEl.style.color = "#DC2626";
        }

        // Web Speech API orqali nutqni matnga o'girish (agar mavjud bo'lsa)
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
          speechRecognition = new SpeechRec();
          speechRecognition.lang = 'en-US';
          speechRecognition.continuous = true;
          speechRecognition.interimResults = true;
          speechRecognition.onresult = (evt) => {
            let transcript = '';
            for (let i = evt.resultIndex; i < evt.results.length; ++i) {
              transcript += evt.results[i][0].transcript + ' ';
            }
            const liveTxt = document.getElementById('speakingLiveTranscript');
            if (liveTxt) liveTxt.textContent = transcript;
            const prodInput = document.getElementById('productionInput');
            if (prodInput && !prodInput.value) prodInput.value = transcript;
          };
          speechRecognition.start();
        }

      } catch (err) {
        alert(isRu ? ("Доступ к микрофону не предоставлен или не поддерживается: " + err.message) : (isEn ? ("Microphone permission denied or not available: " + err.message) : ("Mikrofon ruxsati berilmadi yoki mavjud emas: " + err.message)));
      }
    } else {
      // Yozishni to'xtatish
      mediaRecorder.stop();
      if (recordingInterval) clearInterval(recordingInterval);
      if (speechRecognition) {
        try { speechRecognition.stop(); } catch(e){}
      }
      if (btn) {
        btn.innerHTML = isRu ? "🎙️ Перезаписать" : (isEn ? "🎙️ Re-record" : "🎙️ Qayta yozish");
        btn.style.background = "var(--teal)";
        btn.style.color = "#fff";
      }
      if (statusEl) {
        statusEl.textContent = isRu 
          ? "✅ Запись завершена! Теперь нажмите кнопку оценки ИИ." 
          : (isEn ? "✅ Audio recorded! You can now analyze speech with AI." : "✅ Ovoz yozildi! Endi AI orqali baholash tugmasini bosishingiz mumkin.");
        statusEl.style.color = "#16A34A";
      }
    }
  };

  // ==========================================
  // 6. TADQIQOT ROZILIGI (Research Consent Modal)
  // ==========================================
  window.openResearchConsentModal = function() {
    const modal = document.getElementById('researchConsentModal');
    if (modal) modal.style.display = 'flex';
  };

  window.closeResearchConsentModal = function() {
    const modal = document.getElementById('researchConsentModal');
    if (modal) modal.style.display = 'none';
  };

  window.acceptResearchConsent = function() {
    localStorage.setItem('tilora_consent_accepted', 'true');
    window.closeResearchConsentModal();
    if (window.showToast) {
      window.showToast("Tadqiqotda ishtirok etish va akademik halollik roziligi muvaffaqiyatli saqlandi!", "success");
    }
  };

  // Boshlang'ich sozlamalarni ishga tushirish
  document.addEventListener('DOMContentLoaded', () => {
    applyTranslations();
    applyLowBandwidthState();
    
    // Agar tadqiqot ekrani ochilsa, jadvalni yangilash
    const resBtn = document.querySelector('[data-screen="s_research"]');
    if (resBtn) {
      resBtn.addEventListener('click', () => {
        setTimeout(window.initResearchDashboard, 200);
      });
    }

    // Birinchi kirgan foydalanuvchiga rozilik oynasini eslatish
    if (!localStorage.getItem('tilora_consent_accepted')) {
      setTimeout(() => {
        const badge = document.getElementById('consentBadgeNotice');
        if (badge) badge.style.display = 'inline-flex';
      }, 1500);
    }
  });

})();
