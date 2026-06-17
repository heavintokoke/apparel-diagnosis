from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.analyzer import analyze_information
from app.knowledge import load_knowledge
from app.reporting import export_docx, export_pdf


class CoreWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = load_knowledge(force_refresh=True)

    def test_knowledge_counts(self):
        counts = self.knowledge["counts"]
        self.assertEqual(counts["sections"], 16)
        self.assertEqual(counts["diagnosis_items"], 117)
        self.assertEqual(counts["metrics"], 31)
        self.assertEqual(counts["flows"], 4)

    def test_analysis_and_exports(self):
        package = {
            "combined_text": (
                "公司有季度企划、品类结构、价格带和上新节奏。"
                "订单信息每日更新，跟单表记录延期和质量异常。"
                "库存准确率、发货及时率、返工率、客诉率需要每周复盘。"
            ),
            "stats": {"file_count": 1, "text_chars": 80, "tables": 0},
            "files": [{"filename": "sample.txt", "file_type": "Text", "metadata": {}, "text": "sample"}],
        }
        result = analyze_information(package, self.knowledge)
        self.assertEqual(len(result["sections"]), 16)
        self.assertEqual(len(result["main_lines"]), 6)
        self.assertEqual(len(result["flow_charts"]), 4)
        self.assertEqual(len(result["department_issues"]), 13)
        self.assertGreater(len(result["ninety_day_plan"]), 0)
        self.assertIn("items", result["sections"][0])
        self.assertIn("improvement_action", result["sections"][0]["items"][0])
        for item in result["ninety_day_plan"]:
            for field in ["problem", "goal", "action", "owner", "timeframe", "check_metric", "review_mechanism"]:
                self.assertIn(field, item)

        with tempfile.TemporaryDirectory() as tmp:
            docx_path = export_docx(result, Path(tmp) / "report.docx")
            pdf_path = export_pdf(result, Path(tmp) / "report.pdf")
            self.assertTrue(docx_path.exists())
            self.assertTrue(pdf_path.exists())
            self.assertGreater(docx_path.stat().st_size, 1000)
            self.assertGreater(pdf_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
