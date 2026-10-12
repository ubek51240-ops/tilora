import sys
import unittest

# App yo'lini qo'shish
sys.path.insert(0, ".")

from app.services.path_builder import generate_learning_path
from app.services.l1 import analyze_l1_interference
from app.services.rationale import build_rationale
from app.services.scoring import score_writing_production

class TiloraCoreTests(unittest.TestCase):
    def test_qoida_1_tashvish_surilishi(self):
        """Tashvish > 65 bo'lganda og'zaki nutq 1-slotdan surilishi."""
        path_low = generate_learning_path("st_01", {"speaking": "A2", "listening": "B1"}, anxiety_level=30)
        self.assertEqual(path_low[0]["skill"], "speaking")
        
        path_high = generate_learning_path("st_01", {"speaking": "A2", "listening": "B1"}, anxiety_level=75)
        self.assertEqual(path_high[0]["skill"], "listening")
        self.assertEqual(path_high[1]["skill"], "speaking")
        print(" [PASS] 1-qoida / Metodika: Tashvish qoidasi to'g'ri ishladi.")

    def test_qoida_2_shablonli_sabab(self):
        """2-QOIDA: Har bir tavsiya va materialda asosli sabab bor."""
        rationale = build_rationale("speaking", "A2", 75, "full", "Filologiya")
        self.assertIn("SPEAKING", rationale)
        self.assertIn("tashvishi yuqori", rationale)
        self.assertIn("Filologiya", rationale)
        print(" [PASS] 2-qoida: Shablondan sabab yaratish to'g'ri ishladi.")

    def test_l1_regex_aniqligi(self):
        """Ona tili interferensiyasi kalitsiz regex orqali aniqlanishi."""
        text = "She have many questions and we discuss about this criterias because I am agree."
        issues = analyze_l1_interference(text)
        self.assertGreaterEqual(len(issues), 4)
        print(f" [PASS] L1 interferensiyasi: {len(issues)} ta ona tili xatosi kalitsiz aniqlandi.")

    def test_obektiv_ball(self):
        """Yozma ishni ob'ektiv mezonlar bo'yicha baholash."""
        text = "This is a detailed analysis of learner writing criteria. Teachers should utilize clear rubrics."
        res = score_writing_production(text, 1)
        self.assertIn("rubric", res)
        self.assertIn("total_score", res)
        print(f" [PASS] Ob'ektiv baholash: Ball {res['total_score']}/100 hisoblandi.")

if __name__ == "__main__":
    unittest.main()
