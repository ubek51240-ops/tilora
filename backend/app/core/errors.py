from fastapi import HTTPException, status

ERROR_MESSAGES = {
    "AI_LOCKED": {
        "uz": "Mustaqil bajarish bosqichida sun'iy intellekt vositalaridan foydalanish taqiqlangan. Bu ko'nikmani shakllantirishning asosiy pedagogik qoidasidir.",
        "en": "AI assistance is locked during the independent stage to foster authentic skill acquisition.",
        "ru": "Использование ИИ заблокировано на этапе самостоятельной работы."
    },
    "SELF_RATING_REQUIRED": {
        "uz": "Haqiqiy natijani ko'rish uchun avval o'z baholashingizni (metakognitiv mezonlar bo'yicha) saqlashingiz shart.",
        "en": "Self-rating must be submitted before viewing the actual objective rating.",
        "ru": "Сначала сохраните самооценку перед просмотром объективного результата."
    },
    "NOT_FOUND": {
        "uz": "So'ralgan resurs topilmadi.",
        "en": "Requested resource not found.",
        "ru": "Запрашиваемый ресурс не найден."
    },
    "INVALID_CREDENTIALS": {
        "uz": "Email yoki parol noto'g'ri.",
        "en": "Invalid email or password.",
        "ru": "Неверный адрес электронной почты или пароль."
    },
    "FORBIDDEN_ROLE": {
        "uz": "Ushbu amalni bajarish uchun rolingiz yetarli emas.",
        "en": "Insufficient role permissions for this operation.",
        "ru": "Недостаточно прав для выполнения действия."
    },
    "CONTROL_GROUP_RESTRICTED": {
        "uz": "Nazorat guruhi a'zolariga adaptiv va metakognitiv modullarga kirish taqiqlangan (ilmiy eksperiment dizayni).",
        "en": "Control group members have restricted access to adaptive modules (research integrity).",
        "ru": "Членам контрольной группы закрыт доступ к адаптивным модулям."
    },
    "ASSESSMENT_WINDOW": {
        "uz": "Guruhingizda nazorat (pre/mid/post) o'tkazilmoqda: nazorat texnologik vositalarsiz bajariladi, AI vositalari vaqtincha yopiq.",
        "en": "An assessment window (pre/mid/post) is open for your group: assessments are completed without technology; AI tools are temporarily disabled.",
        "ru": "В вашей группе проходит контроль (pre/mid/post): работа выполняется без технологий, ИИ-инструменты временно отключены."
    },
    "PROPOSAL_ALREADY_DECIDED": {
        "uz": "Ushbu taklif allaqachon ko'rib chiqilgan.",
        "en": "This proposal has already been decided.",
        "ru": "Это предложение уже рассмотрено."
    }
}

class TiloraException(HTTPException):
    def __init__(self, code: str, status_code: int = status.HTTP_400_BAD_REQUEST, locale: str = "uz", details: dict = None):
        msg_dict = ERROR_MESSAGES.get(code, {"uz": code, "en": code, "ru": code})
        detail_msg = msg_dict.get(locale, msg_dict["uz"])
        payload = {
            "error_code": code,
            "message": detail_msg,
            "details": details or {}
        }
        super().__init__(status_code=status_code, detail=payload)
