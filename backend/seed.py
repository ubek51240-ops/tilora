from app.database import SessionLocal, Base, engine
from app.models.entities import User, Institution, Group, StudentProfile
from app.core.security import hash_password

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Baza tozalash yoki mavjud bo'lsa yangilash
    if db.query(User).filter(User.email == "talaba01@tilora.uz").first():
        print("Demo ma'lumotlar allaqachon mavjud.")
        db.close()
        return

    print("Demo ma'lumotlar yuklanmoqda...")
    
    # 1. Muassasalar
    inst1 = Institution(id="inst_buxdu", name="Buxoro davlat universiteti", short_name="BuxDU", direction_code="60110900")
    inst2 = Institution(id="inst_ndpi", name="Nukus davlat pedagogika instituti", short_name="NDPI", direction_code="60110900")
    inst3 = Institution(id="inst_samdchti", name="Samarqand davlat chet tillar instituti", short_name="SamDChTI", direction_code="60230113")
    db.add_all([inst1, inst2, inst3])
    db.commit()
    
    # 2. Guruhlar
    grp_exp = Group(id="grp_302", institution_id=inst1.id, name="302-guruh (Tajriba)", course_year=3, experiment_arm="experimental")
    grp_ctrl = Group(id="grp_304", institution_id=inst1.id, name="304-guruh (Nazorat)", course_year=3, experiment_arm="control")
    db.add_all([grp_exp, grp_ctrl])
    db.commit()
    
    # 3. Foydalanuvchilar
    pwd = hash_password("tilora2026!")
    
    teacher = User(id="usr_teacher_01", email="oqituvchi1@tilora.uz", password_hash=pwd, full_name="Adiba Ikramova", role="teacher", institution_id=inst1.id)
    student1 = User(id="usr_student_01", email="talaba01@tilora.uz", password_hash=pwd, full_name="Aziza Karimova", role="student", institution_id=inst1.id, group_id=grp_exp.id)
    student_ctrl = User(id="usr_student_13", email="talaba13@tilora.uz", password_hash=pwd, full_name="Sardor Umarov", role="student", institution_id=inst1.id, group_id=grp_ctrl.id)
    student_new = User(id="usr_student_24", email="talaba24@tilora.uz", password_hash=pwd, full_name="Madina Aliyeva", role="student", institution_id=inst1.id, group_id=grp_exp.id)
    researcher = User(id="usr_researcher_01", email="tadqiqotchi@tilora.uz", password_hash=pwd, full_name="Tadqiqotchi (Dissertant)", role="researcher", institution_id=inst1.id)
    admin = User(id="usr_admin_01", email="admin@tilora.uz", password_hash=pwd, full_name="Tizim Administratori", role="admin")
    developer = User(id="usr_dev_01", email="dasturchi@tilora.uz", password_hash=pwd, full_name="Dasturchi (API Integrator)", role="developer", is_approved=True)
    
    db.add_all([teacher, student1, student_ctrl, student_new, researcher, admin, developer])
    db.commit()
    
    # 4. Talaba profili
    prof1 = StudentProfile(
        student_id=student1.id,
        cefr_listening="B1",
        cefr_reading="B2",
        cefr_speaking="A2",
        cefr_writing="B1",
        load_capacity=45,
        pace_index=62,
        anxiety_level=71,
        autonomy_readiness=40,
        source="initial_test"
    )
    db.add(prof1)
    db.commit()
    
    print("Demo ma'lumotlar muvaffaqiyatli yuklandi.")
    print("Barcha hisoblar uchun parol: tilora2026!")
    db.close()

if __name__ == "__main__":
    seed_database()
