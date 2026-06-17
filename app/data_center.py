from __future__ import annotations

import json
import re
import shutil
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO

from .config import DATA_DIR, ROOT_DIR
from .extractors import extract_file, normalize_text


DATA_CENTER_DIR = DATA_DIR / "data_center"
MATERIAL_FILE_DIR = DATA_CENTER_DIR / "files"
EXTRACTED_DIR = DATA_CENTER_DIR / "extracted"
MATERIAL_INDEX_PATH = DATA_CENTER_DIR / "materials.json"
REPORT_CENTER_PATH = DATA_DIR / "reports" / "reports.json"

MODULE_IDS = [
    "enterprise-diagnosis",
    "strategy-model",
    "org-position",
    "comp-performance",
    "customer-management",
    "franchise-growth",
    "product-planning",
    "supply-chain",
    "inventory",
    "store-retail",
    "visual-content",
    "short-video",
    "live-commerce",
    "private-domain",
    "data-operation",
    "ai-efficiency",
]

CATEGORY_RULES = [
    ("商品", ["商品", "企划", "款式", "品类", "价格带", "上新", "样衣", "爆款", "滞销"]),
    ("订单", ["订单", "跟单", "交付", "排期", "排产", "延期", "进度"]),
    ("销售", ["销售", "客户", "招商", "成交", "渠道", "会员", "复购"]),
    ("财务", ["财务", "成本", "毛利", "利润", "费用", "应收", "现金流"]),
    ("人效", ["组织", "岗位", "人员", "绩效", "薪酬", "考核", "职责"]),
    ("供应链", ["供应商", "采购", "面料", "辅料", "生产", "车间", "质检", "质量"]),
    ("库存", ["库存", "仓储", "库位", "入库", "出库", "盘点", "库龄"]),
    ("内容运营", ["图片", "视觉", "短视频", "直播", "内容", "素材", "账号"]),
]

_LOCK = threading.RLock()


def safe_filename(filename: str) -> str:
    filename = Path(filename or "upload").name
    filename = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", filename)
    return filename or f"upload_{uuid.uuid4().hex}"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    for directory in [DATA_CENTER_DIR, MATERIAL_FILE_DIR, EXTRACTED_DIR, REPORT_CENTER_PATH.parent]:
        directory.mkdir(parents=True, exist_ok=True)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except ValueError:
        return str(path)


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _empty_material_index() -> dict:
    return {"version": 1, "updated_at": None, "materials": []}


def _empty_report_index() -> dict:
    return {"version": 1, "updated_at": None, "reports": []}


def _material_index() -> dict:
    _ensure_dirs()
    return _load_json(MATERIAL_INDEX_PATH, _empty_material_index())


def _write_material_index(index: dict) -> None:
    index["updated_at"] = _now()
    _write_json(MATERIAL_INDEX_PATH, index)


def _report_index() -> dict:
    _ensure_dirs()
    return _load_json(REPORT_CENTER_PATH, _empty_report_index())


def _write_report_index(index: dict) -> None:
    index["updated_at"] = _now()
    _write_json(REPORT_CENTER_PATH, index)


def _classify_material(filename: str, extracted: dict | None) -> list[str]:
    haystack = f"{filename}\n{(extracted or {}).get('text', '')[:5000]}"
    categories = [
        category
        for category, keywords in CATEGORY_RULES
        if any(keyword in haystack for keyword in keywords)
    ]
    return categories or ["通用资料"]


def _summarize_record(record: dict) -> dict:
    hidden = {"absolute_path", "extracted_absolute_path"}
    return {key: value for key, value in record.items() if key not in hidden}


def list_materials() -> dict:
    with _LOCK:
        index = _material_index()
        materials = [_summarize_record(record) for record in index.get("materials", []) if not record.get("deleted")]
    ready = [record for record in materials if record.get("extract_status") == "ready"]
    category_counts: dict[str, int] = {}
    for record in materials:
        for category in record.get("categories", []):
            category_counts[category] = category_counts.get(category, 0) + 1
    return {
        "ok": True,
        "materials": materials,
        "counts": {
            "total": len(materials),
            "ready": len(ready),
            "failed": len(materials) - len(ready),
            "categories": category_counts,
        },
    }


def _store_stream(stream: BinaryIO, original_filename: str, source_module: str = "data-center") -> dict:
    _ensure_dirs()
    material_id = uuid.uuid4().hex[:12]
    filename = safe_filename(original_filename)
    stored_name = f"{material_id}_{filename}"
    stored_path = MATERIAL_FILE_DIR / stored_name
    extracted_path = EXTRACTED_DIR / f"{material_id}.json"

    with stored_path.open("wb") as target:
        shutil.copyfileobj(stream, target)

    record: dict[str, Any] = {
        "id": material_id,
        "filename": filename,
        "stored_name": stored_name,
        "stored_path": _rel(stored_path),
        "absolute_path": str(stored_path),
        "source_module": source_module or "data-center",
        "uploaded_at": _now(),
        "size": stored_path.stat().st_size,
        "scope": "enterprise",
        "shared_modules": MODULE_IDS,
    }

    try:
        extracted = extract_file(stored_path).to_dict()
        extracted_path.write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")
        record.update(
            {
                "file_type": extracted["file_type"],
                "extract_status": "ready",
                "metadata": extracted.get("metadata", {}),
                "text_chars": len(extracted.get("text", "")),
                "tables": len(extracted.get("tables", [])),
                "text_preview": normalize_text(extracted.get("text", ""))[:260],
                "categories": _classify_material(filename, extracted),
                "extracted_path": _rel(extracted_path),
                "extracted_absolute_path": str(extracted_path),
            }
        )
    except Exception as exc:
        record.update(
            {
                "file_type": stored_path.suffix.lower().lstrip(".").upper() or "Unknown",
                "extract_status": "failed",
                "extract_error": str(exc),
                "metadata": {},
                "text_chars": 0,
                "tables": 0,
                "text_preview": "",
                "categories": _classify_material(filename, None),
                "extracted_path": "",
                "extracted_absolute_path": "",
            }
        )

    with _LOCK:
        index = _material_index()
        index.setdefault("materials", []).insert(0, record)
        _write_material_index(index)

    return _summarize_record(record)


def store_existing_file(path: Path, source_module: str = "data-center") -> dict:
    with path.open("rb") as stream:
        return _store_stream(stream, path.name, source_module)


def store_uploaded_fields(fields: list[Any], source_module: str = "data-center") -> list[dict]:
    records: list[dict] = []
    for field in fields:
        if not getattr(field, "filename", None):
            continue
        records.append(_store_stream(field.file, field.filename, source_module))
    return records


def _records_by_id() -> dict[str, dict]:
    index = _material_index()
    return {record["id"]: record for record in index.get("materials", []) if not record.get("deleted")}


def _selected_records(material_ids: list[str] | None = None, use_all_materials: bool = False) -> list[dict]:
    records_by_id = _records_by_id()
    if use_all_materials:
        records = list(records_by_id.values())
    else:
        requested = [item for item in (material_ids or []) if item]
        missing = [item for item in requested if item not in records_by_id]
        if missing:
            raise ValueError(f"资料中心未找到资料：{', '.join(missing)}")
        records = [records_by_id[item] for item in requested]
    return [record for record in records if record.get("extract_status") == "ready"]


def build_information_package_from_materials(
    material_ids: list[str] | None = None,
    use_all_materials: bool = False,
) -> dict:
    with _LOCK:
        records = _selected_records(material_ids, use_all_materials)
        files: list[dict] = []
        for record in records:
            extracted_path = Path(record.get("extracted_absolute_path") or ROOT_DIR / record.get("extracted_path", ""))
            if not extracted_path.exists():
                continue
            extracted = json.loads(extracted_path.read_text(encoding="utf-8"))
            extracted["material_id"] = record["id"]
            extracted["categories"] = record.get("categories", [])
            files.append(extracted)

    combined = "\n\n".join(f"## {item['filename']}\n{item.get('text', '')}" for item in files if item.get("text"))
    return {
        "files": files,
        "combined_text": normalize_text(combined),
        "material_ids": [item["material_id"] for item in files],
        "stats": {
            "file_count": len(files),
            "text_chars": len(combined),
            "tables": sum(len(item.get("tables", [])) for item in files),
            "ocr_unavailable_files": sum(1 for item in files if str(item.get("metadata", {}).get("ocr_status", "")).startswith("unavailable")),
            "scanned_pdf_candidates": sum(1 for item in files if item.get("metadata", {}).get("scan_status") == "likely_scanned_pdf_or_image_pdf"),
        },
    }


def record_report(
    run_id: str,
    module_id: str,
    title: str,
    result: dict,
    material_ids: list[str],
) -> dict:
    report = {
        "run_id": run_id,
        "module_id": module_id,
        "title": title,
        "created_at": result.get("generated_at") or _now(),
        "updated_at": _now(),
        "material_ids": material_ids,
        "summary": result.get("executive_summary", "")[:260],
        "result_path": _rel(DATA_DIR / "reports" / run_id / "result.json"),
        "exports": {},
    }
    with _LOCK:
        index = _report_index()
        reports = [item for item in index.get("reports", []) if item.get("run_id") != run_id]
        reports.insert(0, report)
        index["reports"] = reports
        _write_report_index(index)
    return report


def record_report_export(run_id: str, export_type: str, path: Path) -> None:
    with _LOCK:
        index = _report_index()
        for report in index.get("reports", []):
            if report.get("run_id") == run_id:
                report.setdefault("exports", {})[export_type] = _rel(path)
                report["updated_at"] = _now()
                break
        _write_report_index(index)


def list_reports() -> dict:
    with _LOCK:
        index = _report_index()
        reports = index.get("reports", [])
    return {"ok": True, "reports": reports, "counts": {"total": len(reports)}}
