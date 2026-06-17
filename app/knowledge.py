from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

from .config import DEFAULT_KNOWLEDGE_DOCX, KNOWLEDGE_CACHE


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W_VAL = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"


def _text_of(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(".//w:t", WORD_NS)).strip()


def _paragraph_style(paragraph: ET.Element) -> str:
    style = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
    return style.attrib.get(W_VAL, "") if style is not None else ""


def _table_rows(table: ET.Element) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.findall("./w:tr", WORD_NS):
        cells = [_text_of(tc) for tc in tr.findall("./w:tc", WORD_NS)]
        if any(cells):
            rows.append(cells)
    return rows


def _section_id(title: str, index: int) -> str:
    cleaned = re.sub(r"^\d+\.\s*", "", title).replace(" / ", "_")
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "_", cleaned).strip("_")
    return f"S{index:02d}_{cleaned}"


def parse_knowledge_docx(docx_path: Path) -> dict:
    if not docx_path.exists():
        raise FileNotFoundError(f"诊断标准文件不存在：{docx_path}")

    with ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml")
    root = ET.fromstring(document_xml)
    body = root.find("w:body", WORD_NS)
    if body is None:
        raise ValueError("无法读取 Word 文档正文")

    sections: list[dict] = []
    flows: list[dict] = []
    main_lines: list[dict] = [
        {"id": "goods", "name": "货的主线", "description": "市场趋势、企划、研发、打版、生产、质检、入仓"},
        {"id": "customer", "name": "客的主线", "description": "线索、需求、报价、看样、下单、交付、复购"},
        {"id": "money", "name": "钱的主线", "description": "销售额、毛利、费用、库存、应收、现金流、净利润"},
        {"id": "people", "name": "人的主线", "description": "老板、管理层、关键岗位、流程、数据、制度"},
    ]

    current: dict | None = None
    section_index = 0
    intro_by_section: dict[str, list[str]] = {}

    for child in list(body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _text_of(child)
            if not text:
                continue
            style = _paragraph_style(child)
            section_match = re.match(r"^(\d+)\.\s*(.+诊断)$", text)
            if style == "3" and section_match:
                section_index += 1
                current = {
                    "id": _section_id(text, section_index),
                    "number": section_index,
                    "title": section_match.group(2),
                    "items": [],
                    "metrics": [],
                    "notes": [],
                }
                sections.append(current)
                intro_by_section[current["id"]] = []
            elif current is not None and style == "4":
                intro_by_section[current["id"]].append(text)
        elif tag == "tbl":
            rows = _table_rows(child)
            if not rows:
                continue
            header = rows[0]
            if len(header) >= 2 and header[0] == "流程":
                flows.extend({"name": row[0], "content": row[1]} for row in rows[1:] if len(row) >= 2)
                continue
            if current is None or len(header) < 2:
                continue
            if header[0] in {"诊断项", "质量节点"}:
                for row in rows[1:]:
                    if len(row) >= 2 and row[0]:
                        current["items"].append(
                            {
                                "name": row[0],
                                "question": row[1],
                                "source_header": header[0],
                            }
                        )
            elif header[0] == "指标":
                for row in rows[1:]:
                    if len(row) >= 2 and row[0]:
                        current["metrics"].append({"name": row[0], "meaning": row[1]})

    for section in sections:
        notes = intro_by_section.get(section["id"], [])
        section["intro"] = notes[0] if notes else ""
        section["focus"] = next((note for note in notes if "解决的是" in note or "重点看" in note), "")

    knowledge = {
        "title": "服装企业全链路穿透式经营诊断",
        "source_docx": str(docx_path),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "main_lines": main_lines,
        "sections": sections,
        "flows": flows,
        "counts": {
            "sections": len(sections),
            "diagnosis_items": sum(
                1
                for section in sections
                for item in section["items"]
                if item.get("source_header") == "诊断项"
            ),
            "quality_nodes": sum(
                1
                for section in sections
                for item in section["items"]
                if item.get("source_header") == "质量节点"
            ),
            "assessment_points": sum(len(section["items"]) for section in sections),
            "metrics": sum(len(section["metrics"]) for section in sections),
            "flows": len(flows),
        },
    }
    return knowledge


def load_knowledge(force_refresh: bool = False) -> dict:
    source = Path(os.environ.get("DIAGNOSIS_KNOWLEDGE_DOCX", DEFAULT_KNOWLEDGE_DOCX))
    if (force_refresh or not KNOWLEDGE_CACHE.exists()) and source.exists():
        knowledge = parse_knowledge_docx(source)
        KNOWLEDGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        KNOWLEDGE_CACHE.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
        return knowledge

    if KNOWLEDGE_CACHE.exists():
        with KNOWLEDGE_CACHE.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    knowledge = parse_knowledge_docx(source)
    KNOWLEDGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_CACHE.write_text(json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8")
    return knowledge


def summarize_counts(knowledge: dict) -> str:
    counts = knowledge["counts"]
    return (
        f"{counts['sections']} 个诊断板块、"
        f"{counts['diagnosis_items']} 个诊断项、"
        f"{counts.get('quality_nodes', 0)} 个质量节点、"
        f"{counts['metrics']} 个关键指标、"
        f"{counts['flows']} 条流程"
    )
