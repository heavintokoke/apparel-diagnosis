from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
REPORT_DIR = DATA_DIR / "reports"
PUBLIC_DIR = ROOT_DIR / "public"
OUTPUT_DIR = ROOT_DIR / "outputs"

DEFAULT_KNOWLEDGE_DOCX = ROOT_DIR / "服装企业全链路穿透式经营诊断.docx"
KNOWLEDGE_CACHE = DATA_DIR / "diagnosis_knowledge.json"

APP_HOST = "127.0.0.1"
APP_PORT = 8765
