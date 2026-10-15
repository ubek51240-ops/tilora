"""
Mavjud jadvallarga yetishmayotgan ustunlarni qo'shish (create_all mavjud jadvalni o'zgartirmaydi).
Dissertatsiya modullari (v2.4) uchun: groups.assessment_window, users.last_login_at, lesson_records.teacher_rubric.
Import paytida bir marta bajariladi (app.api.student / teacher_panel orqali).
"""
from sqlalchemy import inspect, text
from app.database import engine

_NEEDED = {
    "groups": [("assessment_window", "VARCHAR(10)")],
    "users": [("last_login_at", "DATETIME")],
    "lesson_records": [("teacher_rubric", "JSON")],
}

_done = False


def ensure_columns() -> None:
    global _done
    if _done:
        return
    try:
        insp = inspect(engine)
        with engine.begin() as conn:
            for table, cols in _NEEDED.items():
                if table not in insp.get_table_names():
                    continue
                existing = {c["name"] for c in insp.get_columns(table)}
                for col, ctype in cols:
                    if col not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}"))
        _done = True
    except Exception:
        # Baza hali yaratilmagan bo'lsa (testlar), keyingi chaqiruvda qayta uriniladi
        pass


ensure_columns()
