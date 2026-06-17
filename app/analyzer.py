from __future__ import annotations

import re
from datetime import datetime
from typing import Any


RISK_LABELS = {
    "high": "高风险",
    "medium": "中风险",
    "low": "低风险",
}

KEYWORD_SYNONYMS = {
    "公司定位": ["企业定位", "业务定位", "公司类型", "商业定位"],
    "核心客户": ["目标客户", "客户类型", "客户群体", "客户画像"],
    "盈利模式": ["赚钱方式", "利润来源", "收入模式", "商业模式"],
    "竞争优势": ["核心优势", "差异化", "优势资源", "卖点"],
    "增长瓶颈": ["经营瓶颈", "增长问题", "业务卡点", "限制增长"],
    "季度企划": ["商品规划", "季节规划", "春夏秋冬规划", "波段企划"],
    "品类结构": ["品类占比", "品类规划", "类目结构", "货品结构"],
    "价格带": ["价格区间", "价格梯度", "引流款", "利润款"],
    "上新节奏": ["上新计划", "上架节奏", "新品节奏", "波段上新"],
    "款式来源": ["选款来源", "开发来源", "款源", "设计来源"],
    "爆款复盘": ["畅销款复盘", "爆品复盘", "热销款复盘"],
    "滞销复盘": ["滞销款复盘", "动销差", "清仓复盘"],
    "开发命中率": ["采纳率", "选中率", "下单率", "款式命中"],
    "开发周期": ["打样周期", "样衣周期", "出样周期"],
    "打版需求单": ["制版需求", "打样需求", "设计需求单", "款式资料"],
    "纸样管理": ["纸样编号", "纸样归档", "版型档案"],
    "样衣管理": ["样衣档案", "样衣编号", "样衣记录"],
    "修改记录": ["改版记录", "修改次数", "变更记录"],
    "尺码标准": ["尺码表", "尺寸标准", "版型标准"],
    "工艺单": ["工艺资料", "工艺说明", "生产工艺单"],
    "物料齐套": ["齐套率", "物料到齐", "开产齐套"],
    "采购周期": ["到货周期", "交货周期", "面料周期"],
    "订单排期": ["生产排期", "排产计划", "生产计划"],
    "产能评估": ["产能测算", "产能确认", "接单评估"],
    "延期预警": ["交期预警", "延期提醒", "风险预警"],
    "标准工时": ["工时标准", "标准时间", "工序工时"],
    "日产量": ["日产能", "每日产量", "单日产出"],
    "返工率": ["返修率", "重工率", "返工情况"],
    "首件确认": ["首件检", "首件样", "首件审核"],
    "客诉率": ["投诉率", "客户投诉", "售后投诉"],
    "订单信息": ["订单资料", "订单明细", "客户需求"],
    "跟单表": ["生产跟单表", "订单跟进表", "进度表"],
    "进度更新": ["每日更新", "进度同步", "订单进度"],
    "库位管理": ["货位管理", "仓位管理", "库位编号"],
    "库存准确": ["账实一致", "库存准确率", "盘点准确"],
    "发货及时率": ["准时发货率", "及时发货", "履约及时"],
    "客户来源": ["线索来源", "获客渠道", "客户渠道"],
    "客户分层": ["客户等级", "ABC客户", "客户分类"],
    "跟进记录": ["沟通记录", "客户跟进", "拜访记录"],
    "招商漏斗": ["销售漏斗", "转化漏斗", "线索转化"],
    "图片资料": ["产品图", "细节图", "上身图", "素材"],
    "视频内容": ["短视频", "直播素材", "内容素材"],
    "单款成本": ["款式成本", "成本核算", "成本表"],
    "毛利核算": ["毛利率", "单款毛利", "利润核算"],
    "应收账款": ["欠款", "账期", "回款", "应收"],
    "岗位职责": ["岗位说明", "职责边界", "岗位分工"],
    "绩效机制": ["绩效考核", "KPI", "考核机制"],
    "数据工具": ["ERP", "CRM", "Excel", "飞书", "企微", "系统"],
    "数据准确": ["数据口径", "数据及时", "数据质量"],
}


OWNER_MAP = [
    ("商品", "商品负责人"),
    ("研发", "设计研发负责人"),
    ("设计", "设计负责人"),
    ("板", "板房负责人"),
    ("样衣", "板房负责人"),
    ("采购", "采购负责人"),
    ("生产", "生产负责人"),
    ("车间", "车间主管"),
    ("工艺", "工艺负责人"),
    ("质量", "质检负责人"),
    ("跟单", "跟单负责人"),
    ("交付", "跟单负责人"),
    ("仓储", "仓库负责人"),
    ("库存", "仓库负责人"),
    ("销售", "销售负责人"),
    ("客户", "销售负责人"),
    ("招商", "招商负责人"),
    ("线上", "运营负责人"),
    ("视觉", "视觉内容负责人"),
    ("财务", "财务负责人"),
    ("成本", "财务负责人"),
    ("组织", "总经理/人事负责人"),
    ("绩效", "人事负责人"),
    ("数据", "运营管理负责人"),
]

MAIN_LINE_DEFINITIONS = [
    {
        "id": "goods",
        "name": "货的主线",
        "question": "货有没有问题？",
        "description": "商品企划、研发、版型、样衣、面辅料、生产、质量是否顺畅。",
        "section_numbers": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    },
    {
        "id": "customer",
        "name": "客的主线",
        "question": "客有没有问题？",
        "description": "客户来源、销售跟进、招商成交、老客复购是否成体系。",
        "section_numbers": [10, 12, 13, 14],
    },
    {
        "id": "delivery",
        "name": "交付的主线",
        "question": "交付有没有问题？",
        "description": "订单、排产、跟单、车间、质检、发货是否可控。",
        "section_numbers": [5, 6, 7, 8, 9, 10, 11],
    },
    {
        "id": "money",
        "name": "钱的主线",
        "question": "钱有没有问题？",
        "description": "成本、毛利、库存、应收、现金流、费用是否清楚。",
        "section_numbers": [1, 5, 11, 15],
    },
    {
        "id": "people",
        "name": "人的主线",
        "question": "人有没有问题？",
        "description": "岗位、权责、绩效、会议、协同是否清楚。",
        "section_numbers": [1, 6, 10, 16],
    },
    {
        "id": "data",
        "name": "数据的主线",
        "question": "数据有没有问题？",
        "description": "关键数据有没有、准不准、谁负责、有没有用于决策。",
        "section_numbers": list(range(1, 17)),
    },
]


DEPARTMENT_DEFINITIONS = [
    {"name": "老板", "owner": "总经理", "section_numbers": [1, 16], "tokens": ["战略", "商业模式", "老板依赖", "增长瓶颈"]},
    {"name": "商品", "owner": "商品负责人", "section_numbers": [2], "tokens": ["商品企划", "季度企划", "品类结构", "爆款复盘", "滞销复盘"]},
    {"name": "设计", "owner": "设计研发负责人", "section_numbers": [3], "tokens": ["设计研发", "研发方向", "款式开发", "设计资料"]},
    {"name": "板房", "owner": "板房负责人", "section_numbers": [4], "tokens": ["板房", "版型", "样衣", "纸样", "尺码"]},
    {"name": "采购", "owner": "采购负责人", "section_numbers": [5], "tokens": ["采购", "面辅料", "供应商", "物料齐套"]},
    {"name": "跟单", "owner": "跟单负责人", "section_numbers": [10], "tokens": ["跟单", "订单信息", "进度更新", "异常记录"]},
    {"name": "车间", "owner": "车间主管", "section_numbers": [6, 7, 8], "tokens": ["车间", "生产", "排产", "工序", "标准工时", "首件确认"]},
    {"name": "质检", "owner": "质检负责人", "section_numbers": [9], "tokens": ["质量", "质检", "巡检", "尾检", "客诉复盘"]},
    {"name": "仓库", "owner": "仓库负责人", "section_numbers": [11], "tokens": ["仓储", "库存", "库位", "入库", "出库"]},
    {"name": "销售", "owner": "销售负责人", "section_numbers": [12], "tokens": ["销售", "客户", "报价", "跟进记录"]},
    {"name": "运营", "owner": "运营负责人", "section_numbers": [13, 14], "tokens": ["招商", "渠道", "线上内容", "视觉", "直播"]},
    {"name": "财务", "owner": "财务负责人", "section_numbers": [15], "tokens": ["财务", "成本", "毛利", "应收", "现金流"]},
    {"name": "人事行政", "owner": "人事负责人", "section_numbers": [16], "tokens": ["组织", "岗位职责", "绩效", "会议机制"]},
]


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？；;\n])", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def _keywords(name: str, question: str) -> list[str]:
    seeds = [name]
    for part in re.split(r"[，、。；;：:？?\s/]+", question):
        part = part.strip()
        if 2 <= len(part) <= 12:
            seeds.append(part)
    compact = [seed for seed in seeds if seed and seed not in {"是否", "有没有", "哪些", "怎么", "如何"}]
    seen: set[str] = set()
    result: list[str] = []
    for seed in compact:
        if seed not in seen:
            seen.add(seed)
            result.append(seed)
    return _expand_keywords(result)[:14]


def _expand_keywords(keywords: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        candidates = [keyword]
        for seed, synonyms in KEYWORD_SYNONYMS.items():
            if seed in keyword or keyword in seed:
                candidates.extend(synonyms)
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                expanded.append(candidate)
    return expanded


def _find_evidence(text: str, keywords: list[str], limit: int = 2) -> list[str]:
    if not text:
        return []
    sentences = _split_sentences(text)
    hits: list[str] = []
    for sentence in sentences:
        if any(keyword and keyword in sentence for keyword in keywords):
            clean = sentence.replace("\n", " ")
            hits.append(clean[:180])
        if len(hits) >= limit:
            break
    return hits


def _owner_for(title: str) -> str:
    for token, owner in OWNER_MAP:
        if token in title:
            return owner
    return "总经理/项目负责人"


def _risk_from_score(score: int) -> str:
    if score < 35:
        return "high"
    if score < 65:
        return "medium"
    return "low"


def _section_finding(section: dict, score: int, missing_items: list[str]) -> str:
    if score >= 75:
        return f"{section['title']}资料较完整，可作为后续优化基础。"
    if score >= 45:
        return f"{section['title']}已有部分信息，但仍缺少可复盘、可追踪的数据闭环。"
    names = "、".join(missing_items[:3]) if missing_items else "关键流程与数据"
    return f"{section['title']}资料明显不足，优先补齐{names}，否则难以判断真实经营问题。"


def _improvement_action(name: str, owner: str) -> str:
    return f"由{owner}建立“{name}”记录模板，明确口径、责任人、更新频率和周复盘规则。"


def _split_flow_steps(content: str) -> list[str]:
    return [part.strip() for part in re.split(r"\s*→\s*", content or "") if part.strip()]


def _risk_summary(score: int, title: str, missing_names: list[str]) -> str:
    if score >= 75:
        return f"{title}目前资料覆盖较好，重点是保持口径一致和持续复盘。"
    if score >= 45:
        return f"{title}已有部分基础，但仍要补齐{('、'.join(missing_names[:2]) or '关键台账')}。"
    return f"{title}证据不足，应先补齐{('、'.join(missing_names[:3]) or '关键流程、数据和责任人')}。"


def _build_main_lines(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_number = {section["number"]: section for section in sections}
    main_lines: list[dict[str, Any]] = []
    for line in MAIN_LINE_DEFINITIONS:
        linked = [by_number[number] for number in line["section_numbers"] if number in by_number]
        avg_score = round(sum(section["score"] for section in linked) / max(1, len(linked)))
        risk = _risk_from_score(avg_score)
        key_risks = [
            {
                "section": section["title"],
                "score": section["score"],
                "risk_label": section["risk_label"],
                "finding": section["finding"],
            }
            for section in sorted(linked, key=lambda item: (item["score"], item["number"]))[:4]
        ]
        missing = []
        for section in linked:
            missing.extend(section.get("missing_items", [])[:2])
        main_lines.append(
            {
                "id": line["id"],
                "name": line["name"],
                "question": line["question"],
                "description": line["description"],
                "score": avg_score,
                "risk": risk,
                "risk_label": RISK_LABELS[risk],
                "judgment": _risk_summary(avg_score, line["name"], missing),
                "linked_sections": [
                    {
                        "number": section["number"],
                        "title": section["title"],
                        "score": section["score"],
                        "risk_label": section["risk_label"],
                    }
                    for section in linked
                ],
                "key_risks": key_risks,
                "next_actions": [
                    f"先补齐{item['section']}的责任人、数据模板和复盘节奏。"
                    for item in key_risks[:3]
                ],
            }
        )
    return main_lines


def _build_flow_charts(knowledge: dict, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_title = {section["title"]: section for section in sections}
    flow_links = {
        "商品开发流程": ["商品企划诊断", "设计研发诊断", "板房 / 版型 / 样衣诊断", "面辅料与采购诊断", "工艺管理诊断"],
        "订单交付流程": ["生产计划与排产诊断", "生产车间诊断", "质量管理诊断", "生产跟单与交付诊断", "仓储与库存诊断"],
        "客户成交流程": ["销售与客户管理诊断", "招商与渠道诊断", "线上内容与视觉诊断"],
        "异常处理流程": ["生产跟单与交付诊断", "质量管理诊断", "组织、绩效与数据系统诊断"],
    }
    charts: list[dict[str, Any]] = []
    for flow in knowledge.get("flows", []):
        linked = [by_title[title] for title in flow_links.get(flow["name"], []) if title in by_title]
        avg_score = round(sum(section["score"] for section in linked) / max(1, len(linked))) if linked else 0
        risk = _risk_from_score(avg_score)
        weak_points = [
            {
                "section": section["title"],
                "risk_label": section["risk_label"],
                "score": section["score"],
                "finding": section["finding"],
            }
            for section in sorted(linked, key=lambda item: item["score"])[:3]
        ]
        charts.append(
            {
                "name": flow["name"],
                "content": flow["content"],
                "steps": _split_flow_steps(flow["content"]),
                "score": avg_score,
                "risk": risk,
                "risk_label": RISK_LABELS[risk],
                "weak_points": weak_points,
                "improvement_focus": "；".join(point["section"] for point in weak_points) or "补齐流程责任人与记录表单",
            }
        )
    return charts


def _department_matches(department: dict, section: dict) -> bool:
    if section["number"] in department["section_numbers"]:
        return True
    haystack = f"{section['title']} {' '.join(section.get('missing_items', []))}"
    return any(token in haystack for token in department["tokens"])


def _build_department_issues(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    departments: list[dict[str, Any]] = []
    for department in DEPARTMENT_DEFINITIONS:
        linked = [section for section in sections if _department_matches(department, section)]
        missing_items: list[str] = []
        evidence_count = 0
        issues: list[dict[str, Any]] = []
        for section in linked:
            evidence_count += section.get("evidence_count", 0)
            missing_items.extend(section.get("missing_items", [])[:4])
            if section["risk"] in {"high", "medium"}:
                issues.append(
                    {
                        "section": section["title"],
                        "risk_label": section["risk_label"],
                        "problem": section["finding"],
                        "owner": department["owner"],
                        "action": _improvement_action(section["title"], department["owner"]),
                    }
                )
        avg_score = round(sum(section["score"] for section in linked) / max(1, len(linked))) if linked else 0
        risk = _risk_from_score(avg_score)
        departments.append(
            {
                "department": department["name"],
                "owner": department["owner"],
                "score": avg_score,
                "risk": risk,
                "risk_label": RISK_LABELS[risk],
                "linked_sections": [section["title"] for section in linked],
                "missing_items": missing_items[:8],
                "issue_count": len(issues),
                "evidence_count": evidence_count,
                "issues": issues[:6],
                "next_action": (
                    f"由{department['owner']}牵头补齐{('、'.join(missing_items[:3]) or '关键经营数据')}，"
                    "并在周会上复盘异常和改善进度。"
                ),
            }
        )
    return departments


def analyze_information(package: dict, knowledge: dict) -> dict:
    text = package.get("combined_text", "")
    sections_result: list[dict[str, Any]] = []
    missing_data: list[dict[str, str]] = []

    for section in knowledge["sections"]:
        item_results: list[dict[str, Any]] = []
        answered = 0
        for item in section["items"]:
            keywords = _keywords(item["name"], item["question"])
            evidence = _find_evidence(text, keywords)
            status = "covered" if evidence else "missing"
            if evidence:
                answered += 1
            owner = _owner_for(section["title"])
            item_results.append(
                {
                    "name": item["name"],
                    "question": item["question"],
                    "status": status,
                    "status_label": "已有证据" if evidence else "缺少资料",
                    "evidence": evidence,
                    "keywords": keywords,
                    "suggested_owner": owner,
                    "improvement_action": _improvement_action(item["name"], owner),
                }
            )

        metric_results: list[dict[str, Any]] = []
        metric_hits = 0
        for metric in section["metrics"]:
            evidence = _find_evidence(text, _expand_keywords([metric["name"]]), limit=1)
            if evidence:
                metric_hits += 1
            else:
                missing_data.append(
                    {
                        "section": section["title"],
                        "metric": metric["name"],
                        "meaning": metric["meaning"],
                        "suggested_owner": _owner_for(section["title"]),
                    }
                )
            metric_results.append(
                {
                    "name": metric["name"],
                    "meaning": metric["meaning"],
                    "status": "covered" if evidence else "missing",
                    "status_label": "已有证据" if evidence else "缺少数据",
                    "evidence": evidence,
                    "suggested_owner": _owner_for(section["title"]),
                }
            )

        item_total = max(1, len(section["items"]))
        metric_total = max(1, len(section["metrics"]))
        coverage = answered / item_total
        metric_coverage = metric_hits / metric_total if section["metrics"] else coverage
        score = round(coverage * 70 + metric_coverage * 30)
        risk = _risk_from_score(score)
        missing_items = [item["name"] for item in item_results if item["status"] == "missing"]

        sections_result.append(
            {
                "id": section["id"],
                "number": section["number"],
                "title": section["title"],
                "score": score,
                "risk": risk,
                "risk_label": RISK_LABELS[risk],
                "coverage": round(coverage, 2),
                "metric_coverage": round(metric_coverage, 2),
                "finding": _section_finding(section, score, missing_items),
                "intro": section.get("intro", ""),
                "focus": section.get("focus", ""),
                "owner": _owner_for(section["title"]),
                "items": item_results,
                "metrics": metric_results,
                "missing_items": missing_items[:8],
                "evidence_count": sum(len(item["evidence"]) for item in item_results),
            }
        )

    priorities = sorted(
        [section for section in sections_result if section["risk"] in {"high", "medium"}],
        key=lambda section: (section["score"], section["number"]),
    )[:6]

    plan_items = []
    for index, section in enumerate(priorities, start=1):
        first_missing = section["missing_items"][0] if section["missing_items"] else "关键数据"
        metric = next((m["name"] for m in section["metrics"] if m["status"] == "missing"), "复盘完成率")
        plan_items.append(
            {
                "priority": index,
                "problem": section["finding"],
                "goal": f"90 天内把{section['title']}从{section['risk_label']}提升到可跟踪、可复盘状态。",
                "action": f"围绕“{first_missing}”建立标准表单、责任人、周复盘和异常处理机制。",
                "owner": section["owner"],
                "timeframe": "1-30 天建表和补数据；31-60 天跑流程；61-90 天复盘固化。",
                "check_metric": metric,
                "review_mechanism": "每周检查数据更新和异常关闭情况；每月复盘指标变化、责任人动作和下月重点。",
            }
        )

    high_count = sum(1 for section in sections_result if section["risk"] == "high")
    medium_count = sum(1 for section in sections_result if section["risk"] == "medium")
    avg_score = round(sum(section["score"] for section in sections_result) / max(1, len(sections_result)))

    main_lines = _build_main_lines(sections_result)
    flow_charts = _build_flow_charts(knowledge, sections_result)
    department_issues = _build_department_issues(sections_result)

    result = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "local_rules",
        "company_snapshot": "系统已完成资料抽取；请在网页中补充企业名称、规模、主营模式等基础信息后导出正式报告。",
        "executive_summary": (
            f"本次共解析 {package['stats']['file_count']} 个文件，形成 {package['stats']['text_chars']} 个字符的资料包。"
            f"16 个诊断板块平均得分 {avg_score} 分，其中高风险 {high_count} 个、中风险 {medium_count} 个。"
            "当前版本优先识别资料完整度、流程证据和关键指标缺失情况。"
        ),
        "core_findings": [section["finding"] for section in priorities[:5]],
        "root_causes": [
            "关键经营数据没有稳定沉淀，导致问题只能凭经验判断。",
            "部门流程与责任边界证据不足，异常难以及时定位到责任人和改善动作。",
            "商品、客户、交付、财务数据之间尚未形成闭环，影响经营复盘质量。",
        ],
        "short_term_improvements": [
            "先补齐高风险板块的基础台账、责任人和每周复盘机制。",
            "建立统一的订单、样衣、库存、客户、质量异常数据模板。",
            "把缺失指标纳入每周经营会检查清单。",
        ],
        "medium_term_system_build": [
            "将商品开发、订单交付、客户成交、异常处理 4 条流程标准化。",
            "把关键指标绑定到部门负责人，形成月度经营复盘。",
        ],
        "long_term_growth_path": [
            "从老板经验驱动转向流程、数据、团队协同驱动。",
            "逐步沉淀客户画像、爆款复盘、成本利润和供应链履约数据。",
        ],
        "sections": sections_result,
        "main_lines": main_lines,
        "flow_charts": flow_charts,
        "department_issues": department_issues,
        "problem_priorities": [
            {
                "rank": index,
                "section": section["title"],
                "score": section["score"],
                "risk_label": section["risk_label"],
                "reason": section["finding"],
                "owner": section["owner"],
            }
            for index, section in enumerate(priorities, start=1)
        ],
        "missing_data": missing_data[:80],
        "ninety_day_plan": plan_items,
        "source_package": {
            "stats": package["stats"],
            "files": [
                {
                    "filename": file["filename"],
                    "file_type": file["file_type"],
                    "metadata": file["metadata"],
                    "text_preview": file["text"][:500],
                }
                for file in package["files"]
            ],
        },
    }
    return result
