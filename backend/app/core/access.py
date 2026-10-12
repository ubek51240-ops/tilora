from fastapi import Request, status
from app.core.errors import TiloraException

def check_experiment_access(user_arm: str, feature: str):
    """
    Tadqiqot butunligi: Nazorat guruhidagi talabaga adaptiv yo'l va
    metakognitiv blok ko'rsatilmaydi.
    """
    if user_arm == "control" and feature in ["adaptive_path", "metacognitive_block", "ai_scaffold"]:
        raise TiloraException(
            code="CONTROL_GROUP_RESTRICTED",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"experiment_arm": "control", "feature": feature}
        )
    return True
