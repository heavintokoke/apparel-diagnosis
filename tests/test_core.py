from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.analyzer import analyze_information
from app import data_center
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

    def test_data_center_material_reuse_and_report_index(self):
        original_paths = {
            "DATA_CENTER_DIR": data_center.DATA_CENTER_DIR,
            "MATERIAL_FILE_DIR": data_center.MATERIAL_FILE_DIR,
            "EXTRACTED_DIR": data_center.EXTRACTED_DIR,
            "MATERIAL_INDEX_PATH": data_center.MATERIAL_INDEX_PATH,
            "REPORT_CENTER_PATH": data_center.REPORT_CENTER_PATH,
        }
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                data_center.DATA_CENTER_DIR = tmp_path / "data_center"
                data_center.MATERIAL_FILE_DIR = data_center.DATA_CENTER_DIR / "files"
                data_center.EXTRACTED_DIR = data_center.DATA_CENTER_DIR / "extracted"
                data_center.MATERIAL_INDEX_PATH = data_center.DATA_CENTER_DIR / "materials.json"
                data_center.REPORT_CENTER_PATH = tmp_path / "reports" / "reports.json"

                sample = tmp_path / "商品订单销售资料.txt"
                sample.write_text("商品企划、订单信息、销售客户、财务成本和岗位绩效每周复盘。", encoding="utf-8")

                material = data_center.store_existing_file(sample, source_module="enterprise-diagnosis")
                self.assertEqual(material["extract_status"], "ready")
                self.assertIn("商品", material["categories"])

                listed = data_center.list_materials()
                self.assertEqual(listed["counts"]["ready"], 1)

                package = data_center.build_information_package_from_materials([material["id"]])
                self.assertEqual(package["stats"]["file_count"], 1)
                self.assertEqual(package["material_ids"], [material["id"]])
                self.assertIn("订单信息", package["combined_text"])

                result = analyze_information(package, self.knowledge)
                data_center.record_report("testrun001", "enterprise-diagnosis", "测试诊断报告", result, package["material_ids"])
                reports = data_center.list_reports()
                self.assertEqual(reports["counts"]["total"], 1)
                self.assertEqual(reports["reports"][0]["material_ids"], [material["id"]])
        finally:
            for name, value in original_paths.items():
                setattr(data_center, name, value)


if __name__ == "__main__":
    unittest.main()
