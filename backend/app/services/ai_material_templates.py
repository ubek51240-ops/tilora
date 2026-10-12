"""
TILORA AI Generator uchun ko'p tilli (O'zbek, Ingliz, Rus) pedagogik shablonlar banki.
DSc dissertatsiyasi mezonlari va 4 ta asosiy qoida (AI blok, asoslangan izoh, o'qituvchi suvereniteti, metakognitiv refleksiya)
asosida ishlab chiqilgan.
"""
from typing import Any, Dict, List, Optional
import random
import re


def _randomize_question_options(q: Dict[str, Any]) -> Dict[str, Any]:
    """Variantlar o'rnini tasodifiy aralashtirish va correct_index ni to'g'irlash."""
    opts = list(q.get("options") or [])
    if not opts:
        return q
    c_idx = int(q.get("correct_index", 0))
    if not (0 <= c_idx < len(opts)):
        c_idx = 0
    correct_text = opts[c_idx]

    indices = list(range(len(opts)))
    random.shuffle(indices)

    new_opts = [opts[i] for i in indices]
    new_c_idx = new_opts.index(correct_text)

    q_copy = dict(q)
    q_copy["options"] = new_opts
    q_copy["correct_index"] = new_c_idx
    return q_copy


def get_question_pool(
    topic_title: str,
    subject_name: str,
    num_questions: int,
    difficulty: str = "B2",
    language: str = "uz"
) -> List[Dict[str, Any]]:
    """
    O'qituvchi tanlagan til (uz, en, ru) bo'yicha boyitilgan testlar banki.
    """
    lang = (language or "uz").lower()

    if lang == "en":
        raw_bank = [
            {
                "question": f"What is the primary pedagogical objective of the topic '{topic_title}'?",
                "correct": f"Integrating core principles and methodological frameworks of {topic_title} into academic practice",
                "distractors": [
                    "Rote memorization and literal translation of theoretical concepts",
                    "Assigning independent work without pedagogical scaffolding",
                    "Writing essays without adhering to grammatical and academic criteria"
                ],
                "explanation": f"The primary goal is harmonizing theoretical foundations of {topic_title} with practical language competencies."
            },
            {
                "question": f"Which approach most effectively develops learners' metacognitive awareness during a lesson on '{topic_title}'?",
                "correct": "Self-assessment rubrics and structured reflective prompt analysis",
                "distractors": [
                    "Immediate teacher correction of all errors in red ink without explanation",
                    "Copying sample essays verbatim without critical analysis",
                    "Focusing exclusively on final summative test scores"
                ],
                "explanation": "Metacognitive competence relies on learners actively monitoring and evaluating their own cognitive processes."
            },
            {
                "question": f"What pedagogical intervention minimizes L1 (native language) interference in '{topic_title}'?",
                "correct": "Contextualized vocabulary acquisition and target-language collocation analysis",
                "distractors": [
                    "Direct word-for-word translation of idioms and sentences",
                    "Completely avoiding complex syntactic structures",
                    "Repetitive mechanical copying of grammar rules"
                ],
                "explanation": "Studying collocations and formulaic sequences in authentic contexts substantially reduces negative L1 transfer."
            },
            {
                "question": f"In '{subject_name}', what is the essential characteristic of constructive formative feedback?",
                "correct": "Explaining the underlying reason for errors and offering actionable strategies (Rationally grounded)",
                "distractors": [
                    "Assigning only a single numerical grade (e.g. 75/100)",
                    "Having the teacher rewrite every incorrect sentence for the student",
                    "Making vague generalized oral comments at the end of class"
                ],
                "explanation": "According to TILORA Rule 2, all corrective feedback must be rationally grounded with clear explanatory reasons."
            },
            {
                "question": f"Following an analytical language task on '{topic_title}', who must synthesize the final conclusion?",
                "correct": "The student independently (Principle 4: Conclusions are formulated by the learner)",
                "distractors": [
                    "Solely the group leader",
                    "The artificial intelligence generator module",
                    "The academic dean's inspection committee"
                ],
                "explanation": "TILORA Principle 4 establishes that analytical conclusions must be formed autonomously by the student."
            },
            {
                "question": f"How is the principle of Scaffolding practically enacted in '{topic_title}'?",
                "correct": "Providing an initial expert model and support frames, progressively fostering learner autonomy",
                "distractors": [
                    "Requiring autonomous writing without any prior guidelines or exemplars",
                    "Conducting repetitive grammar dictations throughout the session",
                    "Having AI generate all answers and responses for the learners"
                ],
                "explanation": "Scaffolding provides necessary pedagogical support while gradually increasing learner independence."
            },
            {
                "question": f"Which strategy best balances Teacher Talk Time (TTT) and Student Talk Time (STT)?",
                "correct": "Minimizing lecturing and maximizing interactive pair, small-group, and seminar discussions",
                "distractors": [
                    "The teacher speaking for the entire 80-minute class duration",
                    "Confining students strictly to silent individual writing tasks",
                    "Only directing inquiries to top-performing students in the front row"
                ],
                "explanation": "Modern communicative language teaching requires maximizing meaningful student communicative production (STT)."
            },
            {
                "question": f"How can foreign language classroom anxiety (Affective Filter) be alleviated when teaching '{topic_title}'?",
                "correct": "Fostering a supportive climate where errors are treated as constructive stepping stones",
                "distractors": [
                    "Imposing grade penalties for every phonetic or syntactic slip",
                    "Publicly reprimanding students in front of their peers",
                    "Eliminating oral presentations and communicative tasks altogether"
                ],
                "explanation": "A low affective filter creates a safe psychological atmosphere conducive to risk-taking in language production."
            },
            {
                "question": f"What is vital for ensuring high Cohesion and Coherence in academic writing?",
                "correct": "Logical linking connectors, appropriate pronoun referencing, and smooth thematic transitions",
                "distractors": [
                    "Stringing together complex and obscure vocabulary without logical relation",
                    "Starting every sentence with the exact same grammatical subject",
                    "Omitting punctuation and paragraph divisions entirely"
                ],
                "explanation": "Logical connectors and cohesive ties establish structural unity and clarity across the academic text."
            },
            {
                "question": f"What is the primary function of Formative Assessment in higher education?",
                "correct": "Diagnosing ongoing learning gaps to provide timely feedback and guide instructional adjustments",
                "distractors": [
                    "Announcing high-stakes terminal rankings among students",
                    "Fostering unhealthy competitive pressure between peers",
                    "Administering punitive exams containing intentionally obscure trick questions"
                ],
                "explanation": "Formative assessment is designed to support and enhance ongoing learning rather than merely rank learners."
            },
            {
                "question": f"Why is teacher Elicitation essential during seminar discussions?",
                "correct": "It activates existing knowledge and prompts active cognitive involvement from learners",
                "distractors": [
                    "It allows the instructor to immediately deliver ready-made definitions",
                    "It wastes instructional time to shorten the planned syllabus",
                    "It intentionally embarrasses unprepared students"
                ],
                "explanation": "Elicitation transforms learners from passive recipients into active critical thinkers."
            },
            {
                "question": f"When should Instruction Checking Questions (ICQs) be deployed?",
                "correct": "Immediately after giving task instructions to ensure everyone comprehends the expectations",
                "distractors": [
                    "During the final seconds of class as students leave the hall",
                    "Only before the semester final examination",
                    "As a punitive measure for latecomers"
                ],
                "explanation": "ICQs ensure learners understand task mechanics before embarking on independent or collaborative practice."
            },
            {
                "question": f"What inquiry type fosters Critical Thinking when exploring '{topic_title}'?",
                "correct": "Referential, open-ended questions demanding reasoning, evidence, and analytical evaluation",
                "distractors": [
                    "Closed polar questions answerable with a simple 'yes' or 'no'",
                    "Rote questions asking only for dates and arbitrary statistics",
                    "Prompts asking students to read sentences verbatim from a textbook"
                ],
                "explanation": "Referential questions challenge students to analyze, compare, evaluate, and substantiate claims."
            },
            {
                "question": f"What guideline ensures constructive Peer Review among students?",
                "correct": "Utilizing explicit rubric criteria to deliver evidence-based, constructive recommendations",
                "distractors": [
                    "Awarding top scores solely on the basis of friendship",
                    "Relying on subjective personal whims without evaluation criteria",
                    "Publicly mocking errors identified in peer work"
                ],
                "explanation": "Criterion-referenced peer review ensures objective, constructive feedback and bilateral learning."
            },
            {
                "question": f"Why is 'Hedging' essential in academic argumentation?",
                "correct": "To present claims objectively based on scientific probability rather than dogmatic absolutes",
                "distractors": [
                    "To demonstrate a lack of confidence and competence in the subject",
                    "To artificially inflate the overall word count of the paper",
                    "To deliberately confuse and mislead academic reviewers"
                ],
                "explanation": "Hedging (e.g., 'the findings suggest', 'it is plausible that') represents scholarly modesty and objectivity."
            }
        ]

    elif lang == "ru":
        raw_bank = [
            {
                "question": f"В чем заключается основная теоретическая и практическая сущность темы '{topic_title}'?",
                "correct": f"Интеграция ключевых принципов и методической модели {topic_title} в академическую практику",
                "distractors": [
                    "Механическое заучивание и дословный перевод теоретических понятий",
                    "Выполнение самостоятельной работы без методических ориентиров",
                    "Свободное эссе без соблюдения грамматических и академических критериев"
                ],
                "explanation": f"Главная цель занятия — гармонизация теоретических основ {topic_title} с практическими компетенциями."
            },
            {
                "question": f"Какой метод наиболее эффективен для развития метакогнитивных навыков студентов на уроке '{topic_title}'?",
                "correct": "Самооценка (self-assessment) и анализ на основе рефлексивных вопросов",
                "distractors": [
                    "Исправление всех ошибок преподавателем красной пастой без объяснения причин",
                    "Дословное копирование готового образца без аналитической работы",
                    "Ориентация исключительно на итоговый тестовый балл"
                ],
                "explanation": "Метакогнитивная компетентность базируется на осознанном мониторинге собственного процесса познания."
            },
            {
                "question": f"Какая педагогическая мера снижает интерференцию родного языка (L1) в теме '{topic_title}'?",
                "correct": "Изучение контекстуальной академической лексики и устойчивых коллокаций изучаемого языка",
                "distractors": [
                    "Пословный буквальный перевод идиом и сложных синтаксических конструкций",
                    "Полный отказ от использования сложных грамматических структур",
                    "Многократное механическое переписывание грамматических правил"
                ],
                "explanation": "Освоение коллокаций и фразеологических единиц в естественном контексте предотвращает интерференцию."
            },
            {
                "question": f"Что является главным фактором конструктивной обратной связи по дисциплине '{subject_name}'?",
                "correct": "Объяснение причин ошибок и предложение конкретных стратегий улучшения (аргументированный фидбек)",
                "distractors": [
                    "Выставление сухой числовой оценки (например: 75/100) без комментариев",
                    "Полное переписывание текста студента преподавателем",
                    "Общие неконкретные замечания в конце семинарского занятия"
                ],
                "explanation": "Согласно 2-му правилу TILORA, каждая рекомендация должна сопровождаться четким обоснованием причины."
            },
            {
                "question": f"На кого возлагается формулирование итогового вывода после аналитического задания по теме '{topic_title}'?",
                "correct": "На самого студента (4-й принцип: Итоговые выводы делает студент)",
                "distractors": [
                    "Исключительно на старосту учебной группы",
                    "На генеративный модуль искусственного интеллекта",
                    "На инспекционную комиссию деканата"
                ],
                "explanation": "4-й принцип TILORA гласит: итоговое аналитическое заключение студент формирует самостоятельно."
            },
            {
                "question": f"Как на практике проявляется принцип педагогических опор (Scaffolding) в теме '{topic_title}'?",
                "correct": "Демонстрация модельного образца и опорных фраз с поэтапным переходом к автономии учащегося",
                "distractors": [
                    "Требование написать эссе без предварительных инструкций и образцов",
                    "Проведение традиционных диктантов на протяжении всего занятия",
                    "Полная генерация текста искусственным интеллектом за студента"
                ],
                "explanation": "Scaffolding предоставляет необходимую временную поддержку, постепенно повышая независимость студента."
            },
            {
                "question": f"Какой подход оптимален для баланса времени речи преподавателя (TTT) и студентов (STT)?",
                "correct": "Сокращение лекционной части и активизация парных, групповых дискуссий и кейс-стади",
                "distractors": [
                    "Монолог преподавателя на протяжении всех 80 минут аудиторного времени",
                    "Ограничение работы студентов исключительно индивидуальным молчаливым письмом",
                    "Обращение с вопросами только к студентам-отличникам"
                ],
                "explanation": "В коммуникативной методике приоритет отдается максимальному времени речевой практики студентов (STT)."
            },
            {
                "question": f"Как снизить уровень тревожности (Affective Filter) при изучении темы '{topic_title}'?",
                "correct": "Создание доверительной атмосферы, где ошибки воспринимаются как естественный этап обучения",
                "distractors": [
                    "Снижение баллов за каждую незначительную оговорку или грамматическую погрешность",
                    "Публичная жесткая критика студента перед всей аудиторией",
                    "Полное исключение устных презентаций из учебного плана"
                ],
                "explanation": "Низкий аффективный фильтр обеспечивает психологическую безопасность и стимулирует языковую активность."
            },
            {
                "question": f"Что обеспечивает высокую связность и логичность (Coherence & Cohesion) академического текста?",
                "correct": "Корректные логические коннекторы, местоименные связки и четкие тематические переходы",
                "distractors": [
                    "Бессистемное нагромождение редких и сложных терминов",
                    "Начало каждого предложения с одного и того же грамматического оборота",
                    "Отказ от членения текста на абзацы и пунктуации"
                ],
                "explanation": "Логические коннекторы и средства когезии обеспечивают структурное и смысловое единство текста."
            },
            {
                "question": f"Какова основная цель формирующего оценивания (Formative Assessment) в высшей школе?",
                "correct": "Выявление пробелов в режиме реального времени для своевременной педагогической коррекции",
                "distractors": [
                    "Оглашение окончательных итоговых рейтингов и распределение мест",
                    "Создание нездоровой соревновательной атмосферы в группе",
                    "Проведение карательных контрольных работ с вопросами-ловушками"
                ],
                "explanation": "Формирующее оценивание направлено на улучшение и фасилитацию процесса обучения в динамике."
            },
            {
                "question": f"Почему преподавателю важно применять технику Elicitation (извлечение знаний)?",
                "correct": "Она активизирует предшествующий опыт студентов и стимулирует когнитивную вовлеченность",
                "distractors": [
                    "Чтобы преподаватель мог сразу выдать готовые формулировки правил",
                    "Для заполнения паузы и сокращения времени занятия",
                    "С целью поставить студентов в неловкое положение перед группой"
                ],
                "explanation": "Elicitation превращает обучаемых из пассивных слушателей в активных исследователей."
            },
            {
                "question": f"Когда необходимо задавать проверочные вопросы к инструкциям (ICQ)?",
                "correct": "Сразу после объяснения регламента задания, чтобы удостовериться в верном понимании задачи",
                "distractors": [
                    "В последние секунды занятия перед выходом из аудитории",
                    "Только перед итоговым государственным экзаменом",
                    "В качестве наказания опоздавших студентов"
                ],
                "explanation": "ICQ предотвращают ошибки при выполнении упражнений, гарантируя правильное понимание условий."
            },
            {
                "question": f"Какие вопросы способствуют развитию критического мышления по теме '{topic_title}'?",
                "correct": "Проблемные и аналитические открытые вопросы, требующие обоснования и аргументации",
                "distractors": [
                    "Закрытые вопросы, предполагающие лишь односложные ответы 'да' или 'нет'",
                    "Вопросы на механическое воспроизведение дат и статистических данных",
                    "Требование зачитать текст из учебника слово в слово"
                ],
                "explanation": "Проблемные открытые вопросы стимулируют глубинный анализ, оценку и выдвижение гипотез."
            },
            {
                "question": f"Каковы ключевые правила организации взаимного рецензирования (Peer Review)?",
                "correct": "Использование объективных критериев рубрики для предоставления конструктивных рекомендаций",
                "distractors": [
                    "Выставление максимальных баллов только близким друзьям",
                    "Опора исключительно на личные эмоциональные симпатии без критериев",
                    "Высмеивание допущенных сокурсниками грамматических ошибок"
                ],
                "explanation": "Критериальное взаимооценивание обеспечивает объективность и стимулирует взаимное профессиональное развитие."
            },
            {
                "question": f"Зачем в академическом дискурсе применяется прием хеджирования (Hedging)?",
                "correct": "Для объективной презентации выводов на основе научной вероятности, а не догматических утверждений",
                "distractors": [
                    "Чтобы продемонстрировать неуверенность автора в собственных знаниях",
                    "Для искусственного увеличения объема текста статьи или эссе",
                    "С целью намеренно ввести рецензента в заблуждение"
                ],
                "explanation": "Хеджирование (напр. 'данные свидетельствуют', 'представляется вероятным') — норма академической этики."
            }
        ]

    else:
        # Standart O'zbek tili
        raw_bank = [
            {
                "question": f"'{topic_title}' mavzusining asosiy nazariy-amaliy mohiyati nimadan iborat?",
                "correct": f"{topic_title} doirasidagi asosiy tamoyil va metodik modelni to'g'ri qo'llash",
                "distractors": [
                    "Faqat nazariy tushunchalarni yodlash va tarjima qilish",
                    "Pedagogik ko'rsatmalarsiz mustaqil topshiriq topshirish",
                    "Grammatik mezonlarni hisobga olmasdan erkin yozish"
                ],
                "explanation": f"Ushbu darsning bosh maqsadi {topic_title} tamoyillarini akademik va amaliy jarayonda uyg'unlashtirishdir."
            },
            {
                "question": f"Qaysi uslub '{topic_title}' darsida talabalarning metakognitiv ko'nikmasini rivojlantirishga ko'proq xizmat qiladi?",
                "correct": "O'z-o'zini baholash (self-assessment) va reflektiv savollar orqali tahlil qilish",
                "distractors": [
                    "Xatolarni o'qituvchi tomonidan darhol qizil qalamda belgilab berish",
                    "Tayyor insho andozasini o'zgartirishsiz ko'chirib olish",
                    "Faqat yakuniy test natijasiga e'tibor qaratish"
                ],
                "explanation": "Metakognitiv yondashuv o'quvchining o'z bilish jarayonini monitoring qilishiga asoslanadi."
            },
            {
                "question": f"Pedagogik jarayonda '{topic_title}' bo'yicha L1 (ona tili) interferensiyasini kamaytirish uchun nima tavsiya etiladi?",
                "correct": "Kontekstual lug'at va maqsadli tildagi kollokatsiyalarni tahlil qilish",
                "distractors": [
                    "Har bir iborani to'g'ridan-to'g'ri so'zma-so'z tarjima qilish",
                    "Murakkab jumlalardan butunlay voz kechish",
                    "Grammatik qoidalarni ko'p marta yozib chiqish"
                ],
                "explanation": "Kollokatsiya va frazeologik birliklarni tabiiy kontekstda o'rganish interferensiyani keskin kamaytiradi."
            },
            {
                "question": f"'{subject_name}' fanida mazkur mavzu bo'yicha talabalarga konstruktiv teskari aloqa (feedback) berishda eng muhim omil nima?",
                "correct": "Xatoning sababini ko'rsatish va yaxshilash strategiyasini taklif etish (Rationally grounded)",
                "distractors": [
                    "Faqat yakuniy ball (masalan: 75/100) qo'yish bilan cheklanish",
                    "Barcha xatolarni o'qituvchi o'zi to'g'rilab berishi",
                    "Kamchiliklarni darsda umumiy eslatib o'tish"
                ],
                "explanation": "TILORA 2-qoidasiga ko'ra, har bir izoh va taklifning sababi shablonda aniq ko'rsatilishi shart."
            },
            {
                "question": f"Mavzu yuzasidan o'tkazilgan tahliliy mashqdan so'ng xulosa chiqarish kimning zimmasiga yuklatiladi?",
                "correct": "Talabaning o'ziga (4-tamoyil: Xulosani talaba chiqaradi)",
                "distractors": [
                    "Faqat guruh yetakchisiga",
                    "Sun'iy intellekt moduliga",
                    "Dekanat nazorat guruhiga"
                ],
                "explanation": "TILORA tizimining 4-tamoyili: Yakuniy tahliliy xulosani talaba o'zi mustaqil shakllantirishi lozim."
            },
            {
                "question": f"'{topic_title}' mavzusida Scaffolding (bosqichma-bosqich ko'mak) tamoyili qanday amaliyotda namoyon bo'ladi?",
                "correct": "Dastlab namuna (model) taqdim etilib, bosqichma-bosqich talaba mustaqilligi oshirilishi orqali",
                "distractors": [
                    "Talabaga hech qanday yo'l-yo'riq bermasdan mustaqil yozdirish orqali",
                    "Faqat nazariy qoidalarni diktant qilib yozdirish orqali",
                    "Sun'iy intellektga barcha javoblarni yozdirib berish orqali"
                ],
                "explanation": "Scaffolding — ta'lim oluvchiga zarur ko'mak berib, mustaqil ishlash darajasini bosqichma-bosqich oshirishdir."
            },
            {
                "question": f"Dars jarayonida Teacher Talk Time (TTT) va Student Talk Time (STT) mutanosibligini ta'minlashda qaysi usul samarali?",
                "correct": "O'qituvchi ma'ruzasi qisqartirilib, juftlik va guruhlarda interaktiv munozaralarni ko'paytirish",
                "distractors": [
                    "Darsning butun 80 daqiqasida faqat o'qituvchi gapirishi",
                    "Talabalarni faqat yozma topshiriq bilan band qilish",
                    "Savollarni faqat eng a'lochi talabalarga berish"
                ],
                "explanation": "Zamonaviy kommunikativ metodikada STT (talaba nutq vaqti) ustun bo'lishi maqsadga muvofiq."
            },
            {
                "question": f"'{topic_title}' kontekstida talabalarning FL (chet tili) tashvishi va hissiy to'sig'ini (Affective Filter) kamaytirish uchun nima zarur?",
                "correct": "Xatolarga o'rganishning tabiiy qismi sifatida qarab, qo'llab-quvvatlovchi muhit yaratish",
                "distractors": [
                    "Har bir fonetik yoki grammatik xato uchun jarima ballari qo'yish",
                    "Talabalarni butun guruh oldida keskin tanqid qilish",
                    "Og'zaki javoblarni darsdan butunlay chiqarib tashlash"
                ],
                "explanation": "Past affektiv to'siq (Low affective filter) talabalarning tildan erkin foydalanishiga zamin yaratadi."
            },
            {
                "question": f"Akademik yozuv va nutqda fikrlar izchilligini (Cohesion & Coherence) ta'minlashda eng muhim vosita nima?",
                "correct": "Mantiqiy konnektorlar, olmoshli bog'lanishlar va mavzuga mos o'tish iboralaridan to'g'ri foydalanish",
                "distractors": [
                    "Faqat murakkab va uzun so'zlarni ketma-ket joylashtirish",
                    "Har bir gapni bir xil so'z bilan boshlash",
                    "Tinish belgilaridan butunlay voz kechish"
                ],
                "explanation": "Konnektorlar va referensial bog'lovchilar matnning mantiqiy yaxlitligini ta'minlaydi."
            },
            {
                "question": f"Dars yakunida o'tkaziladigan Formativ baholashning (Formative Assessment) asosiy maqsadi nima?",
                "correct": "O'quv jarayonidagi bo'shliqlarni aniqlab, dars davomida o'z vaqtida tuzatish kiritish",
                "distractors": [
                    "Faqat yakuniy reyting ballini e'lon qilish",
                    "Talabalarni bir-biri bilan raqobatga solish",
                    "Faqat eng qiyin savollardan iborat imtihon o'tkazish"
                ],
                "explanation": "Formativ baholash ta'lim jarayonini o'z vaqtida takomillashtirishga qaratilgan."
            },
            {
                "question": f"O'qituvchining Elicitation (fikrni tortib chiqarish) texnikasidan foydalanishi nima uchun muhim?",
                "correct": "Talabalarning mavjud bilimlarini faollashtirib, faol kognitiv ishtirokini ta'minlash uchun",
                "distractors": [
                    "Tayyor javobni darhol o'qituvchi o'zi aytib berishi uchun",
                    "Vaqtni behuda sarflash va darsni cho'zish uchun",
                    "Talabalarni qiyin ahvolga solib sinash uchun"
                ],
                "explanation": "Elicitation talabalarni passiv tinglovchidan faol fikrlovchiga aylantiradi."
            },
            {
                "question": f"Instruction Checking Questions (ICQ) — ko'rsatmani tekshiruvchi savollardan qachon foydalaniladi?",
                "correct": "Topshiriq berilgach, talabalar vazifa shartini to'g'ri tushunganini tekshirish uchun",
                "distractors": [
                    "Darsning eng oxirgi daqiqasida xayrlashuv oldidan",
                    "Faqat yakuniy imtihon qoidalarini e'lon qilganda",
                    "Darsga kechikkan talabalarni jazolash paytida"
                ],
                "explanation": "ICQ ko'rsatmalar noaniqligi sababli topshiriq noto'g'ri bajarilishining oldini oladi."
            },
            {
                "question": f"'{topic_title}' bo'yicha talabalarda tanqidiy fikrlashni (Critical Thinking) rivojlantirish uchun qanday savollar ko'proq berilishi kerak?",
                "correct": "Referensial (ochiq, tahliliy va mulohazaga chorlovchi) savollar",
                "distractors": [
                    "Faqat 'ha' yoki 'yo'q' deb javob beriladigan yopiq savollar",
                    "Faqat sana va raqamlarni so'rovchi yodlash savollari",
                    "Faqat kitobdagi matnni so'zma-so'z o'qib berishni talab qiluvchi savollar"
                ],
                "explanation": "Referensial savollar chuqur kognitiv tahlil va shaxsiy dalillashni talab qiladi."
            },
            {
                "question": f"Tengdoshlararo baholash (Peer Review) jarayonida talabalarga qanday yo'l-yo'riq berilishi lozim?",
                "correct": "Aniq rubrika mezonlari asosida konstruktiv va ijobiy takliflar bildirish",
                "distractors": [
                    "Faqat do'stining ishiga eng yuqori ball qo'yish",
                    "Hech qanday mezonlarsiz faqat shaxsiy yoqish-yoqmaslikka tayanish",
                    "Boshqalarning xatolarini kulgiga olish"
                ],
                "explanation": "Rubrikaga tayangan peer review xolislik va o'zaro o'rganishni ta'minlaydi."
            },
            {
                "question": f"Akademik tilda dalillash (Argumentation) paytida 'Hedging' (ehtiyotkorlik bilan xulosa qilish) nima uchun kerak?",
                "correct": "Fikrlarni mutlaq haqiqat deb emas, balki ilmiy ehtimollik va faktlar asosida xolisona taqdim etish uchun",
                "distractors": [
                    "O'z fikriga ishonchsizlikni ko'rsatish uchun",
                    "Matn hajmini sun'iy ravishda ko'paytirish uchun",
                    "O'quvchini ataylab chalg'itish uchun"
                ],
                "explanation": "Hedging (masalan: 'evidence suggests', 'it is probable that') ilmiy etika va xolislik belgisidir."
            }
        ]

    selected = []
    for i in range(num_questions):
        raw = raw_bank[i % len(raw_bank)]
        all_options = [raw["correct"]] + list(raw["distractors"])
        q_obj = {
            "id": f"q_{i + 1}",
            "question": raw["question"],
            "options": all_options,
            "correct_index": 0,
            "explanation": raw["explanation"]
        }
        selected.append(_randomize_question_options(q_obj))

    return selected


def get_slide_blueprints(topic_title: str, subject_name: str, language: str = "uz") -> List[Dict[str, Any]]:
    """O'qituvchi tanlagan til bo'yicha 15 ta slayd shablonlari."""
    lang = (language or "uz").lower()

    if lang == "en":
        return [
            {
                "title": f"Topic: {topic_title}",
                "visual_badge": "INTRODUCTION & PLAN",
                "bullets": [
                    f"Subject: {subject_name} · University Course",
                    "Format: Adaptive-Metacognitive Interactive Seminar",
                    "Primary Goal: Acquire academic & practical competencies",
                    "Target Outcome: Apply theoretical models to independent tasks"
                ],
                "speaker_notes": "Welcome, esteemed students. Today we will explore this topic following our 5-stage lesson model.",
                "image_prompt": f"Modern university lecture hall, lecturer at podium presenting {topic_title}, educational infographics, professional minimalist style"
            },
            {
                "title": "Learning Objectives & Expected Competencies",
                "visual_badge": "LEARNING OBJECTIVES",
                "bullets": [
                    "Master core theoretical foundations (CEFR B2-C1 benchmark)",
                    "Analyze lexical-grammatical and stylistic criteria",
                    "Autonomous written and spoken language production",
                    "Cultivate self-assessment (metacognitive monitoring) skills"
                ],
                "speaker_notes": "By the end of this session, each learner will formulate an autonomous analytical conclusion on the topic.",
                "image_prompt": f"Academic learning goals, target diagram and competence roadmap for studying '{topic_title}', {subject_name}, modern educational presentation visual"
            },
            {
                "title": "Core Theoretical Framework & Principles",
                "visual_badge": "THEORY & MODEL",
                "bullets": [
                    f"Pedagogical and scientific essence of {topic_title}",
                    "Essential academic terminology and collocations",
                    "Common interference errors and preventative techniques",
                    "Exemplary model analysis and empirical evidence"
                ],
                "speaker_notes": "Let us focus on the practical realization of theoretical concepts. We will deconstruct the given models together.",
                "image_prompt": f"Scientific conceptual framework, theoretical model and structure of '{topic_title}', {subject_name}, academic lecture visualization"
            },
            {
                "title": "Practical Stage: Modeling & Scaffolding Analysis",
                "visual_badge": "PRACTICAL MODELING",
                "bullets": [
                    "Deconstruct an authentic academic text or pedagogical case",
                    "Isolate support scaffolds and transitional linkers",
                    "Analytical criteria: Coherence, precision, stylistic conformity",
                    "Diagnose error sources using diagnostic rubrics"
                ],
                "speaker_notes": "Examine the organizational structure in this sample. You are expected to mirror this rigor in your independent tasks.",
                "image_prompt": f"Students and researcher analyzing practical case study and literature about '{topic_title}', {subject_name}, clean scholarly environment"
            },
            {
                "title": "Interactive Task: Collaborative Pair Analysis",
                "visual_badge": "INTERACTIVE PAIR WORK",
                "bullets": [
                    "Simulate authentic classroom pedagogical scenarios",
                    "Protocol for structured peer review",
                    "Step-by-step analytical execution strategy",
                    "Rule 1 Reminder: AI tools are locked during the independent stage"
                ],
                "speaker_notes": "Now let us transition to collaborative practice. Discuss the prompt with your partner and formulate reasoned proposals.",
                "image_prompt": f"Collaborative university workshop discussing '{topic_title}', students analyzing concepts together, {subject_name}, bright modern classroom"
            },
            {
                "title": "Pedagogical Case Study & Classroom Scenario",
                "visual_badge": "CASE STUDY",
                "bullets": [
                    "Analyze authentic pedagogical dilemmas in language learning",
                    "Root causes and underlying cognitive factors",
                    "Actionable interventions: Differential support and guidance",
                    "Group presentation and constructive dialogue"
                ],
                "speaker_notes": "In this case study, accounting for individual learner differences is paramount. What strategies do you propose?",
                "image_prompt": f"Case study analysis and critical problem solving regarding '{topic_title}', {subject_name}, university seminar group project"
            },
            {
                "title": "Linguistic Error Patterns & L1 Interference",
                "visual_badge": "ERROR ANALYSIS",
                "bullets": [
                    "Negative transfer from native language structures",
                    "Syntactic, lexical, and stylistic dissonance",
                    "Actionable methods for mitigating mother-tongue transfer",
                    "Delivering constructive, rationale-grounded feedback"
                ],
                "speaker_notes": "Errors are a natural component of language acquisition. The priority is diagnosing L1 transfer and applying targeted corrections.",
                "image_prompt": f"Error analysis chart, comparative diagnostic checklist and structural evaluation for '{topic_title}', {subject_name}"
            },
            {
                "title": "Formative Assessment & Analytical Rubrics",
                "visual_badge": "ASSESSMENT CRITERIA",
                "bullets": [
                    "Overview of 4 core evaluation rubrics",
                    "Task fulfillment and substantive depth",
                    "Lexical sophistication and grammatical control",
                    "Rule 3: Final evaluation rests with teacher sovereignty"
                ],
                "speaker_notes": "Analytical rubrics ensure transparency, showing each student precisely where and how to refine their performance.",
                "image_prompt": f"Assessment rubric scorecard and performance evaluation criteria for '{topic_title}', {subject_name}, professional infographic"
            },
            {
                "title": "Classroom Dynamics: Balancing TTT and STT",
                "visual_badge": "CLASSROOM DYNAMICS",
                "bullets": [
                    "Optimizing Teacher Talk Time vs Student Talk Time",
                    "Open-ended prompts stimulating critical discourse",
                    "Mitigating Foreign Language Classroom Anxiety (Affective Filter)",
                    "Active listening and constructive facilitation"
                ],
                "speaker_notes": "Student talk and thinking time should dominate our sessions. The teacher serves as an active facilitator.",
                "image_prompt": f"Engaging university seminar discussion and interactive teaching dialogue about '{topic_title}', {subject_name}, auditorium setting"
            },
            {
                "title": "Metacognitive Reflection & Self-Assessment",
                "visual_badge": "REFLECTION",
                "bullets": [
                    "Top 3 key insights synthesized from today's lesson",
                    "Completing the self-assessment grid",
                    "Diagnosing cognitive hurdles and areas for growth",
                    "Setting personal academic goals for the upcoming phase"
                ],
                "speaker_notes": "Log into your platform profile and respond to the reflective prompts. Autonomously assess your learning progress.",
                "image_prompt": f"Student writing in reflective study journal about '{topic_title}', metacognitive thinking, {subject_name}, calm lighting"
            },
            {
                "title": "Scholarly Research & Educational Implications",
                "visual_badge": "SCHOLARLY RESEARCH",
                "bullets": [
                    f"Recent empirical findings regarding {topic_title}",
                    "Bridging academic theory and contemporary classroom practice",
                    "The Teacher-Researcher paradigm",
                    "Data-informed pedagogical decision-making"
                ],
                "speaker_notes": "Familiarity with scholarly publications on this topic will substantially enrich your future graduation dissertations.",
                "image_prompt": f"Academic research papers, scientific publications and data analytics regarding '{topic_title}', {subject_name}, scholarly atmosphere"
            },
            {
                "title": "Summary, Autonomous Assignment & Next Steps",
                "visual_badge": "SUMMARY & TASK",
                "bullets": [
                    "Synthesis of key competencies and essential takeaways",
                    "Independent assignment: Mini-investigation on the topic",
                    "Platform submission deadline: Before next class session",
                    "Brief preview of subsequent syllabus topics"
                ],
                "speaker_notes": "Thank you for your active participation. Remember to upload your independent assignment by the stated deadline!",
                "image_prompt": f"Summary roadmap, syllabus milestones and independent project assignment on '{topic_title}', {subject_name}, clean minimal design"
            },
            {
                "title": "Recommended Academic Bibliography",
                "visual_badge": "BIBLIOGRAPHY",
                "bullets": [
                    "Core and supplementary syllabus textbooks",
                    "International peer-reviewed journals and repositories",
                    "Curated digital modules on the TILORA platform",
                    "Selected references for self-directed reading"
                ],
                "speaker_notes": "These selected resources and digital publications are recommended for in-depth independent study.",
                "image_prompt": f"University library curated scholarly textbooks and academic literature on '{topic_title}', {subject_name}"
            },
            {
                "title": "Student Inquiries, Q&A and Discussion",
                "visual_badge": "Q&A SESSION",
                "bullets": [
                    "Open floor for inquiries and concept clarifications",
                    "Summary reflections shared by collaborative pairs",
                    "Instructor synthesis and guiding commentary",
                    "Rapid pulse check on instructional efficacy"
                ],
                "speaker_notes": "Let us open the floor to questions. What observations or questions have emerged from your analysis?",
                "image_prompt": f"Interactive Q&A academic forum and student questions regarding '{topic_title}', {subject_name}, university lecture"
            },
            {
                "title": "Course Milestones & Assessment Guidelines",
                "visual_badge": "ANNOUNCEMENTS",
                "bullets": [
                    "Preparation requirements for the midterm evaluation",
                    "Portfolio compilation criteria and milestones",
                    "Attendance and classroom participation records",
                    "Wishing everyone a productive and inspired academic week!"
                ],
                "speaker_notes": "Thank you for your engagement today! See you in the next session.",
                "image_prompt": f"Academic achievement, university course certificate and honors in studying '{topic_title}', {subject_name}"
            }
        ]

    elif lang == "ru":
        return [
            {
                "title": f"Тема: {topic_title}",
                "visual_badge": "ВВЕДЕНИЕ И ПЛАН",
                "bullets": [
                    f"Предмет: {subject_name} · Университетское образование",
                    "Формат: Адаптивно-метакогнитивный интерактивный семинар",
                    "Главная цель: Освоение академических и практических компетенций",
                    "Ожидаемый результат: Применение теории в самостоятельной работе"
                ],
                "speaker_notes": "Здравствуйте, уважаемые студенты. Сегодня мы изучаем новую тему в рамках 5-этапной модели урока.",
                "image_prompt": f"Modern university lecture hall, lecturer at podium presenting {topic_title}, educational infographics, professional minimalist style"
            },
            {
                "title": "Цели урока и ожидаемые результаты",
                "visual_badge": "УЧЕБНЫЕ ЦЕЛИ",
                "bullets": [
                    "Освоение теоретической базы (требования CEFR B2-C1)",
                    "Анализ лексико-грамматических и стилистических критериев",
                    "Навыки самостоятельной письменной и устной речи",
                    "Формирование навыков самооценки и метакогнитивного мониторинга"
                ],
                "speaker_notes": "К концу занятия каждый студент должен самостоятельно сформулировать аналитический вывод по теме.",
                "image_prompt": f"Academic learning goals, target diagram and competence roadmap for studying '{topic_title}', {subject_name}, modern educational presentation visual"
            },
            {
                "title": "Ключевая теоретическая концепция и правила",
                "visual_badge": "ТЕОРИЯ И МОДЕЛЬ",
                "bullets": [
                    f"Научно-педагогическая сущность {topic_title}",
                    "Базовые термины и академические коллокации",
                    "Типичные ошибки интерференции и их профилактика",
                    "Анализ модельного образца и научная аргументация"
                ],
                "speaker_notes": "Обратим внимание на практическое выражение теории. Проанализируем представленные примеры.",
                "image_prompt": f"Scientific conceptual framework, theoretical model and structure of '{topic_title}', {subject_name}, academic lecture visualization"
            },
            {
                "title": "Практический этап: Образец и анализ (Scaffolding)",
                "visual_badge": "ОБРАЗЕЦ И АНАЛИЗ",
                "bullets": [
                    "Разбор модельного академического текста или ситуации",
                    "Опорные конструкции (scaffolds) и связующие элементы",
                    "Критерии: связность, точность и соответствие стилю",
                    "Выявление источников ошибок по диагностической сетке"
                ],
                "speaker_notes": "Разберем структуру образца. Рекомендуется придерживаться именно этого порядка при выполнении работы.",
                "image_prompt": f"Students and researcher analyzing practical case study and literature about '{topic_title}', {subject_name}, clean scholarly environment"
            },
            {
                "title": "Интерактивная работа: Анализ в парах (Peer Work)",
                "visual_badge": "РАБОТА В ПАРАХ",
                "bullets": [
                    "Моделирование реальной учебной ситуации",
                    "Порядок проведения взаимного анализа (Peer review)",
                    "Пошаговая стратегия выполнения задания",
                    "Напоминание (Правило 1): На этапе самостоятельной работы ИИ заблокирован"
                ],
                "speaker_notes": "Переходим к парной работе. Обсудите ситуацию с партнером и предложите свои решения.",
                "image_prompt": f"Collaborative university workshop discussing '{topic_title}', students analyzing concepts together, {subject_name}, bright modern classroom"
            },
            {
                "title": "Педагогический кейс-стади и практическая ситуация",
                "visual_badge": "КЕЙС-СТАДИ",
                "bullets": [
                    "Анализ реальной учебной проблемы в аудитории",
                    "Причины возникновения и когнитивные факторы",
                    "Пути решения: дифференцированный подход и поддержка",
                    "Презентация и дискуссия в группе"
                ],
                "speaker_notes": "В данном кейсе важно учесть индивидуальные особенности учащихся. Какие решения вы предложите?",
                "image_prompt": f"Case study analysis and critical problem solving regarding '{topic_title}', {subject_name}, university seminar group project"
            },
            {
                "title": "Лингвистические ошибки и интерференция L1",
                "visual_badge": "АНАЛИЗ ОШИБОК",
                "bullets": [
                    "Влияние структур родного языка на изучаемый язык",
                    "Анализ синтаксических и лексических несоответствий",
                    "Практические рекомендации по снижению интерференции",
                    "Методы конструктивной обратной связи"
                ],
                "speaker_notes": "Ошибки — естественная часть обучения. Важно своевременно замечать влияние родного языка.",
                "image_prompt": f"Error analysis chart, comparative diagnostic checklist and structural evaluation for '{topic_title}', {subject_name}"
            },
            {
                "title": "Формирующее оценивание и аналитические рубрики",
                "visual_badge": "КРИТЕРИИ ОЦЕНКИ",
                "bullets": [
                    "4 ключевых критерия оценки письменной и устной речи",
                    "Полнота выполнения задачи (Task Fulfillment)",
                    "Лексическое богатство и грамматическая точность",
                    "Правило 3: Итоговая оценка остается прерогативой преподавателя"
                ],
                "speaker_notes": "Аналитическая рубрика позволяет каждому студенту четко видеть зоны для развития.",
                "image_prompt": f"Assessment rubric scorecard and performance evaluation criteria for '{topic_title}', {subject_name}, professional infographic"
            },
            {
                "title": "Баланс общения и техника Elicitation",
                "visual_badge": "БАЛАНС ОБЩЕНИЯ",
                "bullets": [
                    "Соотношение Teacher Talk Time (TTT) и Student Talk Time (STT)",
                    "Открытые вопросы для стимулирования мышления студентов",
                    "Снижение языковой тревожности (FL anxiety)",
                    "Активное слушание и конструктивный диалог"
                ],
                "speaker_notes": "Время речи студентов на занятии должно быть максимальным. Преподаватель выступает фасилитатором.",
                "image_prompt": f"Engaging university seminar discussion and interactive teaching dialogue about '{topic_title}', {subject_name}, auditorium setting"
            },
            {
                "title": "Метакогнитивная рефлексия и самооценка",
                "visual_badge": "РЕФЛЕКСИЯ",
                "bullets": [
                    "3 главных вывода сегодняшнего занятия",
                    "Заполнение листа самооценки (Self-assessment grid)",
                    "Определение и анализ сложных аспектов",
                    "Постановка личных учебных целей на следующий этап"
                ],
                "speaker_notes": "Войдите в профиль на платформе и заполните рефлексивный лист. Оцените свою учебную деятельность.",
                "image_prompt": f"Student writing in reflective study journal about '{topic_title}', metacognitive thinking, {subject_name}, calm lighting"
            },
            {
                "title": "Научно-практические исследования и импликации",
                "visual_badge": "ИССЛЕДОВАНИЯ",
                "bullets": [
                    f"Современные международные исследования по теме {topic_title}",
                    "Применение современных методик в практическом обучении",
                    "Модель преподавателя-исследователя (Teacher-Researcher)",
                    "Принятие педагогических решений на основе фактов"
                ],
                "speaker_notes": "Изучение научной литературы по данной теме поможет в будущих выпускных квалификационных работах.",
                "image_prompt": f"Academic research papers, scientific publications and data analytics regarding '{topic_title}', {subject_name}, scholarly atmosphere"
            },
            {
                "title": "Итоги занятия и самостоятельное задание",
                "visual_badge": "ИТОГИ И ЗАДАНИЕ",
                "bullets": [
                    "Основные выводы урока и синтез компетенций",
                    "Самостоятельная работа: аналитическое мини-исследование",
                    "Срок сдачи задания на платформе TILORA",
                    "Краткий анонс следующей темы"
                ],
                "speaker_notes": "Благодарим за активное участие. Не забудьте загрузить самостоятельную работу в срок!",
                "image_prompt": f"Summary roadmap, syllabus milestones and independent project assignment on '{topic_title}', {subject_name}, clean minimal design"
            },
            {
                "title": "Рекомендуемая академическая литература",
                "visual_badge": "ЛИТЕРАТУРА",
                "bullets": [
                    "Основная и дополнительная литература по силлабусу",
                    "Международные научные журналы и электронные ресурсы",
                    "Цифровые материалы, прикрепленные на платформе TILORA",
                    "Дополнительные источники для самостоятельного чтения"
                ],
                "speaker_notes": "Для углубленного изучения темы рекомендуются указанные издания и материалы платформы.",
                "image_prompt": f"University library curated scholarly textbooks and academic literature on '{topic_title}', {subject_name}"
            },
            {
                "title": "Вопросы студентов и интерактивное обсуждение",
                "visual_badge": "ВОПРОСЫ И ОТВЕТЫ",
                "bullets": [
                    "Открытый микрофон по сложным вопросам",
                    "Выводы и комментарии по итогам работы в парах",
                    "Дополнительные направляющие комментарии преподавателя",
                    "Экспресс-оценка эффективности урока"
                ],
                "speaker_notes": "Переходим к вопросам. Какие мысли или предложения у вас возникли по теме?",
                "image_prompt": f"Interactive Q&A academic forum and student questions regarding '{topic_title}', {subject_name}, university lecture"
            },
            {
                "title": "Педагогические заметки и критерии аттестации",
                "visual_badge": "ОБЪЯВЛЕНИЯ",
                "bullets": [
                    "Требования к подготовке к промежуточному тесту",
                    "Критерии и сроки сдачи студенческого портфолио",
                    "Объявление баллов за посещаемость и активность",
                    "Желаем продуктивной учебной недели!"
                ],
                "speaker_notes": "Спасибо за внимание! До встречи на следующем занятии.",
                "image_prompt": f"Academic success, graduation concept, university emblem, modern campus architecture"
            }
        ]

    else:
        return [
            {
                "title": f"Mavzu: {topic_title}",
                "visual_badge": "KIRISH & REJA",
                "bullets": [
                    f"Fan: {subject_name} · Universitet ta'limi",
                    "Dars shakli: Adaptiv-metakognitiv interaktiv seminar",
                    "Asosiy maqsad: Mavzu bo'yicha akademik va amaliy kompetensiyalarni egallash",
                    "Kutilayotgan natija: Nazariy tushunchalarni mustaqil faoliyatda qo'llash"
                ],
                "speaker_notes": "Assalomu alaykum, hurmatli talabalar. Bugungi mashg'ulotimizda dars rejasiga muvofiq yangi mavzuni tahlil qilamiz. Dars 5 bosqichli model asosida olib boriladi.",
                "image_prompt": f"Modern university lecture hall, teacher at podium presenting {topic_title}, educational infographics on screens, professional minimal style"
            },
            {
                "title": "Darsning Maqsadi va Kutilayotgan Natijalar",
                "visual_badge": "O'QUV MAQSADLARI",
                "bullets": [
                    "Mavzuning nazariy poydevorini o'zlashtirish (CEFR B2-C1 talablari)",
                    "Leksik-grammatik va uslubiy mezonlarni to'g'ri tahlil qilish",
                    "Mustaqil yozma va og'zaki nutqda erkin qo'llash mahorati",
                    "O'z-o'zini baholash (metakognitiv monitoring) ko'nikmasini shakllantirish"
                ],
                "speaker_notes": "Dars yakunida har biringiz mazkur mavzu bo'yicha mustaqil tahliliy xulosa chiqarish va amaliy topshiriqni talab darajasida bajarish darajasiga yetishingiz lozim.",
                "image_prompt": f"Academic learning goals, target diagram and competence roadmap for studying '{topic_title}', {subject_name}, modern educational presentation visual"
            },
            {
                "title": "Asosiy Nazariy Konseptsiya va Qoidalar",
                "visual_badge": "NAZARIYA & MODEL",
                "bullets": [
                    f"{topic_title}ning ilmiy-pedagogik mohiyati va tamoyillari",
                    "Mavzuga oid tayanch terminlar va akademik kollokatsiyalar",
                    "Ko'p uchraydigan interferension xatolar va ularning profilaktikasi",
                    "Namunaviy model va ilmiy dalillar tahlili"
                ],
                "speaker_notes": "E'tiborni nazariy tushunchalarning amaliy ifodasiga qaratamiz. Berilgan namunalarni birgalikda tahlil qilamiz.",
                "image_prompt": f"Scientific conceptual framework, theoretical model and structure of '{topic_title}', {subject_name}, academic lecture visualization"
            },
            {
                "title": "Amaliy Bosqich: Namuna va Matn Tahlili (Scaffolding)",
                "visual_badge": "AMALIY NAMUNA",
                "bullets": [
                    "Namunaviy akademik matn yoki pedagogik situatsiyani ko'rib chiqish",
                    "Tayanch iboralar (scaffolds) va strukturaviy bog'lovchilarni ajratish",
                    "Tahlil mezonlari: Koherentlik, aniqlik va lingvistik muvofiqlik",
                    "Xatolar manbasini shablon yordamida aniqlash"
                ],
                "speaker_notes": "Ushbu namunada ko'rsatilgan strukturani tahlil qilamiz. Siz ham o'z topshirig'ingizda aynan shu tartibga amal qilishingiz maqsadga muvofiq.",
                "image_prompt": f"Students and researcher analyzing practical case study and literature about '{topic_title}', {subject_name}, clean scholarly environment"
            },
            {
                "title": "Interaktiv Mashg'ulot: Juftlikda Tahlil (Peer Work)",
                "visual_badge": "INTERAKTIV ISH",
                "bullets": [
                    "Real ta'limiy situatsiyani modellashtirish",
                    "Juftlikda o'zaro tahlil (Peer review) o'tkazish tartibi",
                    "Topshiriqni bosqichma-bosqich bajarish strategiyasi",
                    "1-qoida eslatmasi: Mustaqil bosqichda AIdan tayyor nusxa ko'chirish taqiqlanadi"
                ],
                "speaker_notes": "Endi amaliy mashg'ulotga o'tamiz. Har biringiz juftingiz bilan berilgan vaziyatni muhokama qilib, o'z takliflaringizni bildiring.",
                "image_prompt": f"Collaborative university workshop discussing '{topic_title}', students analyzing concepts together, {subject_name}, bright modern classroom"
            },
            {
                "title": "Pedagogik Keys-Stadi va Amaliy Vaziyat",
                "visual_badge": "KEYS-STADI",
                "bullets": [
                    "Auditoriyada uchraydigan real pedagogik muammo tahlili",
                    "Muammoning kelib chiqish sabablari va kognitiv omillar",
                    "Yechim yo'llari: Differensial yondashuv va individual ko'mak",
                    "Guruh taqdimoti va munozara o'tkazish"
                ],
                "speaker_notes": "Ushbu keys-stadida ta'lim oluvchilarning individual xususiyatlarini hisobga olish muhim. Qanday yechim taklif qilasiz?",
                "image_prompt": f"Case study analysis and critical problem solving regarding '{topic_title}', {subject_name}, university seminar group project"
            },
            {
                "title": "Lingvistik Xatolar va L1 Interferensiyasi Tahlili",
                "visual_badge": "XATOLAR TAHLILI",
                "bullets": [
                    "Ona tili (o'zbek/rus) tuzilmalarining chet tiliga salbiy ta'siri",
                    "Sintaktik va leksik nomutanosibliklar tahlili",
                    "Interferensiyani kamaytirish bo'yicha amaliy tavsiyalar",
                    "Konstruktiv tuzatish usullari (Constructive feedback)"
                ],
                "speaker_notes": "Xatolar — tabiiy o'rganish jarayonining bir qismi. Muhimi, ona tili ta'siridagi xatolarni o'z vaqtida payqab, ularni tuzatishdir.",
                "image_prompt": f"Error analysis chart, comparative diagnostic checklist and structural evaluation for '{topic_title}', {subject_name}"
            },
            {
                "title": "Formativ Baholash va Analitik Rubrikalar",
                "visual_badge": "BAHOLASH MEZONI",
                "bullets": [
                    "Topshiriqni baholashning 4 ta asosiy mezoni",
                    "Mazmun va topshiriq talablarining to'liq bajarilishi (Task Fulfillment)",
                    "Leksik boylik va grammatik aniqlik darajasi",
                    "3-qoida: Yakuniy baholash o'qituvchi suverenitetida qoladi"
                ],
                "speaker_notes": "Baholash rubrikasi orqali har bir talaba o'z ishining qaysi jihatlarini kuchaytirishi kerakligini aniq ko'ra oladi.",
                "image_prompt": f"Assessment rubric scorecard and performance evaluation criteria for '{topic_title}', {subject_name}, professional infographic"
            },
            {
                "title": "Muloqot Balansi va Elicitation Texnikasi",
                "visual_badge": "MULOQOT BALANSI",
                "bullets": [
                    "Teacher Talk Time (TTT) vs Student Talk Time (STT) me'yori",
                    "Talabalarning mustaqil fikrini rag'batlantiruvchi ochiq savollar",
                    "Auditoriyadagi affektiv to'siqlarni (FL anxiety) yumshatish",
                    "Faol tinglash va konstruktiv munosabat bildirish"
                ],
                "speaker_notes": "Darsda talabaning gapirish va fikrlash vaqti maksimal bo'lishi kerak. O'qituvchi yo'naltiruvchi moderator rolida bo'ladi.",
                "image_prompt": f"Engaging university seminar discussion and interactive teaching dialogue about '{topic_title}', {subject_name}, auditorium setting"
            },
            {
                "title": "Metakognitiv Refleksiya va O'z-o'zini Baholash",
                "visual_badge": "REFLEKSIYA",
                "bullets": [
                    "Bugungi darsdan olingan 3 ta eng muhim tushuncha",
                    "O'z-o'zini baholash varaqasi (Self-assessment grid)",
                    "Qiyinchilik tug'dirgan jihatlarni aniqlash va tahlil qilish",
                    "Keyingi bosqich uchun shaxsiy ta'limiy maqsad belgilash"
                ],
                "speaker_notes": "Platformada shaxsiy profilingizga kiring va refleksiya savollariga mustaqil javob yozing. O'z o'rganish jarayoningizni baholang.",
                "image_prompt": f"Student writing in reflective study journal about '{topic_title}', metacognitive thinking, {subject_name}, calm lighting"
            },
            {
                "title": "Ilmiy-Amaliy Tadqiqotlar va Implikatsiyalar",
                "visual_badge": "ILMIY IMPLIKATSIYA",
                "bullets": [
                    f"{topic_title} sohasidagi so'nggi xalqaro tadqiqot natijalari",
                    "Zamonaviy metodologiyaning amaliy ta'limga tatbiqi",
                    "Tadqiqotchi-o'qituvchi (Teacher-Researcher) modeli",
                    "Empirik dalillarga tayangan pedagogik qarorlar qabul qilish"
                ],
                "speaker_notes": "Ushbu mavzu bo'yicha ilmiy manbalarni o'rganish kelgusi bitiruv malakaviy ishlarida ham asqotadi.",
                "image_prompt": f"Academic research papers, scientific publications and data analytics regarding '{topic_title}', {subject_name}, scholarly atmosphere"
            },
            {
                "title": "Yakuniy Xulosa va Mustaqil Topshiriq",
                "visual_badge": "XULOSA & VAZIFA",
                "bullets": [
                    "Darsning asosiy xulosalari va kompetensiyalar sintezi",
                    "Mustaqil vazifa: Mavzu bo'yicha tahliliy mini-tadqiqot tayyorlash",
                    "Tizim platformasida topshiriqni yuklash muddati: keyingi darsgacha",
                    "Keyingi mashg'ulot mavzusiga qisqacha anons"
                ],
                "speaker_notes": "Faol ishtirokingiz uchun barchangizga rahmat. Platformadagi mustaqil vazifani belgilangan muddatgacha yuklashni unutmang!",
                "image_prompt": f"Summary roadmap, syllabus milestones and independent project assignment on '{topic_title}', {subject_name}, clean minimal design"
            },
            {
                "title": "Tavsiya Etiladigan Akademik Adabiyotlar",
                "visual_badge": "ADABIYOTLAR",
                "bullets": [
                    "Asosiy va qo'shimcha darsliklar ro'yxati (Sillabus bo'yicha)",
                    "Xalqaro ilmiy jurnallar va elektron ta'lim resurslari",
                    "TILORA platformasidagi biriktirilgan raqamli materiallar",
                    "Mustaqil mutolaa uchun qo'shimcha havolalar"
                ],
                "speaker_notes": "Mavzuni chuqurroq o'rganishni istagan talabalar uchun ushbu adabiyotlar va platformadagi elektron kitoblar tavsiya etiladi.",
                "image_prompt": f"University library curated scholarly textbooks and academic literature on '{topic_title}', {subject_name}"
            },
            {
                "title": "Talabalar Savol-Javoblari va Muhokama",
                "visual_badge": "SAVOL-JAVOB",
                "bullets": [
                    "Tushunarsiz qolgan jihatlar yuzasidan ochiq mikrofon",
                    "Juftliklar va guruhlarning umumiy xulosalari",
                    "O'qituvchi tomonidan yo'naltiruvchi qo'shimcha sharhlar",
                    "Dars samaradorligi bo'yicha tezkor qayta aloqa"
                ],
                "speaker_notes": "Endi savollarga o'tamiz. Mavzu bo'yicha qanday fikr yoki takliflaringiz bor?",
                "image_prompt": f"Interactive Q&A academic forum and student questions regarding '{topic_title}', {subject_name}, university lecture"
            },
            {
                "title": "Pedagogik Eslatmalar va Baholash Kriteriylari",
                "visual_badge": "ESLATMA",
                "bullets": [
                    "Oraliq nazorat testiga tayyorgarlik talablari",
                    "Portfolio topshirish mezonlari va muddatlari",
                    "Davomat va auditoriyadagi faollik ballari e'loni",
                    "Barchaga muvaffaqiyatli ta'limiy hafta tilaymiz!"
                ],
                "speaker_notes": "E'tiboringiz uchun tashakkur! Keyingi darsda ko'rishguncha.",
                "image_prompt": f"Academic success, graduation concept, university emblem, modern campus architecture"
            }
        ]


def get_slide_pool(
    topic_title: str,
    subject_name: str,
    num_slides: int,
    with_images: bool,
    language: str = "uz"
) -> List[Dict[str, Any]]:
    """
    O'qituvchi tanlagan aniq slaydlar soniga mos ravishda ko'p tilli slaydlar to'plami.
    """
    from app.services.ai_service import get_topic_slide_images

    blueprints = get_slide_blueprints(topic_title, subject_name, language)
    images = get_topic_slide_images(topic_title, subject_name, max(num_slides, 1))

    selected_slides = []
    if num_slides <= len(blueprints):
        if num_slides == 1:
            indices = [0]
        elif num_slides == 2:
            indices = [0, 11]
        else:
            step = (len(blueprints) - 2) / (num_slides - 1)
            indices = [0]
            for step_i in range(1, num_slides - 1):
                idx = 1 + int(step_i * step)
                if idx >= len(blueprints) - 1:
                    idx = len(blueprints) - 2
                indices.append(idx)
            indices.append(11 if 11 < len(blueprints) else len(blueprints) - 1)
        selected_slides = [blueprints[i] for i in indices]
    else:
        selected_slides = [blueprints[i % len(blueprints)] for i in range(num_slides)]

    import random
    from app.services.ai_service import build_ai_image_url

    result = []
    for i, s in enumerate(selected_slides, 1):
        s_copy = dict(s)
        s_copy["slide_number"] = i
        photo = images[(i - 1) % len(images)] if images else ""
        if with_images:
            slide_seed = random.randint(100000, 9999999)
            s_copy["image_url"] = build_ai_image_url(
                prompt=s.get("image_prompt") or s.get("title") or topic_title,
                seed=slide_seed,
                topic=topic_title,
                subject=subject_name
            )
            s_copy["image_fallback_url"] = photo
            s_copy["image_source"] = "ai"
        else:
            s_copy["image_url"] = ""
            s_copy["image_fallback_url"] = ""
            s_copy["image_source"] = "none"
        result.append(s_copy)

    return result


def get_lesson_plan(
    topic_title: str,
    subject_name: str,
    book_title: Optional[str] = None,
    language: str = "uz"
) -> Dict[str, Any]:
    """5 bosqichli dars ssenariysi (O'zbek, Rus yoki Ingliz tilida)."""
    lang = (language or "uz").lower()

    if lang == "en":
        return {
            "title": f"Lesson Plan: {topic_title}" + (f" ({book_title})" if book_title else ""),
            "subject": subject_name,
            "topic": topic_title,
            "book_title": book_title,
            "duration": "80 minutes",
            "language": "en",
            "stages": [
                {
                    "stage": 1,
                    "name": "Orientation & Objectives",
                    "duration": "10 minutes",
                    "activity": "Activate prior knowledge (Brainstorming), present core learning objectives and success criteria.",
                    "teacher_role": "Facilitate elicitation questions, foster intellectual curiosity.",
                    "student_role": "Share initial perspectives, analyze target outcomes and expectations."
                },
                {
                    "stage": 2,
                    "name": "Scaffolding & Modeling",
                    "duration": "15 minutes",
                    "activity": "Deconstruct an academic model text, provide scaffold phrases and structural patterns.",
                    "teacher_role": "Analyze model structure, unpack rubrics and linguistic conventions.",
                    "student_role": "Examine conventions, record core academic vocabulary and linking frames."
                },
                {
                    "stage": 3,
                    "name": "Independent Practice (AI-Locked)",
                    "duration": "30 minutes",
                    "activity": "Learners autonomously produce their analytical text/task. Rule 1: AI generation tools are locked.",
                    "teacher_role": "Circulate to observe progress, monitor individual bottlenecks.",
                    "student_role": "Draft analytical response independently without pre-generated AI shortcuts."
                },
                {
                    "stage": 4,
                    "name": "Analysis & Formative Feedback",
                    "duration": "15 minutes",
                    "activity": "Review error patterns using criteria rubrics, provide rationale-grounded constructive feedback.",
                    "teacher_role": "Deliver constructive feedback explaining causes, model corrections on the board.",
                    "student_role": "Understand root causes of errors, apply targeted revisions."
                },
                {
                    "stage": 5,
                    "name": "Metacognitive Reflection",
                    "duration": "10 minutes",
                    "activity": "Students evaluate their learning trajectory, achievements, and complete self-assessment.",
                    "teacher_role": "Pose reflective prompts, synthesize key takeaways.",
                    "student_role": "Assess personal learning strategies and set individual goals for the next phase."
                }
            ]
        }

    elif lang == "ru":
        return {
            "title": f"План урока: {topic_title}" + (f" ({book_title})" if book_title else ""),
            "subject": subject_name,
            "topic": topic_title,
            "book_title": book_title,
            "duration": "80 минут",
            "language": "ru",
            "stages": [
                {
                    "stage": 1,
                    "name": "Введение и целеполагание (Orientation)",
                    "duration": "10 минут",
                    "activity": "Активизация базовых знаний студентов (Brainstorming), оглашение учебных целей и критериев успеха.",
                    "teacher_role": "Проведение интерактивного опроса, пробуждение познавательного интереса.",
                    "student_role": "Высказывание идей, осмысление целей и ожидаемых результатов."
                },
                {
                    "stage": 2,
                    "name": "Подготовка и поддержка (Scaffolding)",
                    "duration": "15 минут",
                    "activity": "Демонстрация модельного образца, предоставление ключевых фраз и академических шаблонов.",
                    "teacher_role": "Анализ модели, разъяснение критериев и правил.",
                    "student_role": "Изучение структуры, фиксация ключевой терминологии."
                },
                {
                    "stage": 3,
                    "name": "Самостоятельная практика (Independent Practice)",
                    "duration": "30 минут",
                    "activity": "Студенты самостоятельно выполняют письменное или аналитическое задание. Правило 1: ИИ-инструменты заблокированы.",
                    "teacher_role": "Мониторинг процесса, выявление индивидуальных затруднений.",
                    "student_role": "Самостоятельное критическое мышление и написание работы без готовых ИИ-шаблонов."
                },
                {
                    "stage": 4,
                    "name": "Анализ и обратная связь (Analysis & Feedback)",
                    "duration": "15 минут",
                    "activity": "Разбор причин ошибок на основе критериев, предоставление конструктивной обратной связи.",
                    "teacher_role": "Аргументированная обратная связь, разбор типичных ошибок у доски.",
                    "student_role": "Понимание причин ошибок, внесение качественных исправлений."
                },
                {
                    "stage": 5,
                    "name": "Метакогнитивная рефлексия (Reflection)",
                    "duration": "10 минут",
                    "activity": "Студенты формулируют выводы о личном прогрессе, достижениях и заполняют лист самооценки.",
                    "teacher_role": "Постановка рефлексивных вопросов, подведение итогов урока.",
                    "student_role": "Оценка собственных учебных стратегий, постановка целей на будущее."
                }
            ]
        }

    else:
        return {
            "title": f"Dars Ishlanmasi: {topic_title}" + (f" ({book_title})" if book_title else ""),
            "subject": subject_name,
            "topic": topic_title,
            "book_title": book_title,
            "duration": "80 daqiqa",
            "language": "uz",
            "stages": [
                {
                    "stage": 1,
                    "name": "Kirish va Maqsad (Orientation)",
                    "duration": "10 daqiqa",
                    "activity": "Mavzu bo'yicha talabalarning dastlabki bilimlarini faollashtirish (Brainstorming), o'quv maqsadlarini e'lon qilish.",
                    "teacher_role": "Savol-javob o'tkazish, qiziqish uyg'otish.",
                    "student_role": "O'z fikrlarini bildirish, maqsadlarni aniqlashtirish."
                },
                {
                    "stage": 2,
                    "name": "Tayyorgarlik va Ko'mak (Scaffolding)",
                    "duration": "15 daqiqa",
                    "activity": "Namunaviy matn yoki modelni ko'rsatish, tayanch iboralar va akademik andozani taqdim etish.",
                    "teacher_role": "Modelni tahlil qilish, qoidalar asosini tushuntirish.",
                    "student_role": "Tuzilmani o'rganish, tayanch leksikani qayd qilish."
                },
                {
                    "stage": 3,
                    "name": "Mustaqil Amaliyot (Independent Practice)",
                    "duration": "30 daqiqa",
                    "activity": "Talaba o'z bilimi bilan matn/insho yaratadi yoki vazifani bajaradi. 1-qoida: AI vositalari bloklangan.",
                    "teacher_role": "Jarayonni kuzatish, individual qiyinchiliklarni monitoring qilish.",
                    "student_role": "Mustaqil fikrlab yozish, tashqi tayyor yechimlarsiz ishlash."
                },
                {
                    "stage": 4,
                    "name": "Tahlil va Tuzatish (Analysis & Feedback)",
                    "duration": "15 daqiqa",
                    "activity": "Xatolar sababini shablon asosida ko'rib chiqish, konstruktiv tuzatish takliflarini berish.",
                    "teacher_role": "Sababli feedback berish, umumiy xatolarni doskada tahlil qilish.",
                    "student_role": "O'z xatolari ildizini tushunish, tuzatishlarni kiritish."
                },
                {
                    "stage": 5,
                    "name": "Metakognitiv Refleksiya (Reflection)",
                    "duration": "10 daqiqa",
                    "activity": "Talaba dars davomidagi o'sishi, yutuq va kamchiliklari haqida mustaqil xulosa chiqaradi.",
                    "teacher_role": "Refleksiv savollar berish, darsni umumlashtirish.",
                    "student_role": "O'z o'rganish strategiyasini baholash va keyingi maqsadni belgilash."
                }
            ]
        }
