from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"


AI_OUTPUT_FIELDS = [
    "company_snapshot",
    "executive_summary",
    "core_findings",
    "root_causes",
    "short_term_improvements",
    "medium_term_system_build",
    "long_term_growth_path",
    "main_lines",
    "flow_charts",
    "department_issues",
    "missing_data",
    "ninety_day_plan",
]


def _compact_for_ai(local_result: dict) -> dict:
    return {
        "company_snapshot": local_result.get("company_snapshot", ""),
        "executive_summary": local_result.get("executive_summary", ""),
        "core_findings": local_result.get("core_findings", []),
        "root_causes": local_result.get("root_causes", []),
        "main_lines": local_result.get("main_lines", []),
        "flow_charts": local_result.get("flow_charts", []),
        "department_issues": local_result.get("department_issues", []),
        "missing_data": local_result.get("missing_data", [])[:60],
        "sections": [
            {
                "number": section.get("number"),
                "title": section.get("title"),
                "score": section.get("score"),
                "risk_label": section.get("risk_label"),
                "finding": section.get("finding"),
                "owner": section.get("owner"),
                "missing_items": section.get("missing_items", [])[:8],
                "items": [
                    {
                        "name": item.get("name"),
                        "question": item.get("question"),
                        "status_label": item.get("status_label"),
                        "evidence": item.get("evidence", [])[:2],
                    }
                    for item in section.get("items", [])[:12]
                ],
                "metrics": [
                    {
                        "name": metric.get("name"),
                        "meaning": metric.get("meaning"),
                        "status_label": metric.get("status_label"),
                    }
                    for metric in section.get("metrics", [])[:8]
                ],
            }
            for section in local_result.get("sections", [])
        ],
        "ninety_day_plan": local_result.get("ninety_day_plan", []),
    }


def build_manual_ai_prompt(local_result: dict, package: dict, knowledge: dict) -> str:
    output_schema = {
        "company_snapshot": "企业现状判断，字符串",
        "executive_summary": "经营诊断摘要，字符串",
        "core_findings": ["核心问题1", "核心问题2"],
        "root_causes": ["根因1", "根因2"],
        "short_term_improvements": ["1-30天动作"],
        "medium_term_system_build": ["31-60天系统建设"],
        "long_term_growth_path": ["61-90天后增长路径"],
        "main_lines": [
            {
                "id": "goods/customer/delivery/money/people/data",
                "name": "主线名称",
                "judgment": "主线判断",
                "next_actions": ["动作1", "动作2"],
            }
        ],
        "department_issues": [
            {
                "department": "部门名称",
                "owner": "负责人",
                "risk_label": "高风险/中风险/低风险",
                "issues": [{"problem": "问题", "action": "动作"}],
                "next_action": "下一步动作",
            }
        ],
        "ninety_day_plan": [
            {
                "problem": "问题",
                "goal": "目标",
                "action": "动作",
                "owner": "负责人",
                "timeframe": "时间",
                "check_metric": "检查指标",
                "review_mechanism": "复盘机制",
            }
        ],
    }
    return (
        "你是服装企业全链路穿透式经营诊断顾问。请基于下方资料包、本地规则诊断和诊断标准，"
        "对结果做经营顾问级增强：补充真实经营判断、问题优先级、部门责任、流程卡点和90天改善动作。\n\n"
        "输出要求：\n"
        "1. 只输出一个严格 JSON 对象，不要 Markdown，不要解释。\n"
        "2. 不要编造资料中没有的硬数据；缺数据时明确写“待补充/待核实”。\n"
        "3. 保留 16 个板块、4 条流程、部门问题清单、90 天计划的结构。\n"
        "4. ninety_day_plan 每项必须包含 problem, goal, action, owner, timeframe, check_metric, review_mechanism。\n\n"
        f"期望 JSON 字段示例：{json.dumps(output_schema, ensure_ascii=False)}\n\n"
        f"诊断标准：{knowledge.get('title')}；统计：{json.dumps(knowledge.get('counts', {}), ensure_ascii=False)}\n\n"
        f"本地规则诊断结果：{json.dumps(_compact_for_ai(local_result), ensure_ascii=False)}\n\n"
        f"资料包摘录：{package.get('combined_text', '')[:18000]}"
    )


def _extract_output_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    chunks: list[str] = []
    for item in response.get("output", []) or []:
        for content in item.get("content", []) or []:
            if isinstance(content, dict):
                if isinstance(content.get("text"), str):
                    chunks.append(content["text"])
                elif isinstance(content.get("output_text"), str):
                    chunks.append(content["output_text"])
    return "\n".join(chunks).strip()


def _parse_json_block(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("AI 返回内容中没有 JSON 对象")
    return json.loads(match.group(0))


def enhance_with_ai(local_result: dict, package: dict, knowledge: dict) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        local_result["ai_status"] = "未配置 OPENAI_API_KEY，已使用本地规则诊断；可使用 ChatGPT 半自动增强。"
        return local_result

    model = os.environ.get("OPENAI_MODEL", "gpt-5.5")
    compact_sections = [
        {
            "title": section["title"],
            "score": section["score"],
            "risk_label": section["risk_label"],
            "finding": section["finding"],
            "missing_items": section["missing_items"][:5],
        }
        for section in local_result["sections"]
    ]
    prompt = {
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": (
                    "你是服装企业经营诊断顾问。基于资料包和本地规则诊断结果，输出严格 JSON，"
                    "字段必须包含 company_snapshot, executive_summary, core_findings, root_causes, "
                    "short_term_improvements, medium_term_system_build, long_term_growth_path, "
                    "main_lines, flow_charts, department_issues, ninety_day_plan。"
                    "ninety_day_plan 每项包含 problem, goal, action, owner, timeframe, check_metric, review_mechanism。"
                    "不要输出 Markdown。\n\n"
                    f"诊断标准：{knowledge['title']}，共 {knowledge['counts']['sections']} 个板块。\n\n"
                    f"本地规则结果：{json.dumps(compact_sections, ensure_ascii=False)}\n\n"
                    f"资料包摘录：{package.get('combined_text', '')[:18000]}"
                ),
            }
        ],
    }
    body = json.dumps(
        {
            "model": model,
            "input": [prompt],
            "max_output_tokens": 5000,
            "store": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        RESPONSES_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        ai_text = _extract_output_text(payload)
        ai_json = _parse_json_block(ai_text)
        for field in AI_OUTPUT_FIELDS:
            if field in ai_json:
                local_result[field] = ai_json[field]
        if isinstance(ai_json.get("ninety_day_plan"), list) and ai_json["ninety_day_plan"]:
            local_result["ninety_day_plan"] = ai_json["ninety_day_plan"]
        local_result["mode"] = "ai_enhanced"
        local_result["ai_status"] = f"已使用 OpenAI Responses API 增强分析，模型：{model}"
        return local_result
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")[:500]
        local_result["ai_status"] = f"AI 调用失败，已保留本地规则诊断。HTTP {exc.code}: {detail}"
        return local_result
    except Exception as exc:
        local_result["ai_status"] = f"AI 调用失败，已保留本地规则诊断。{exc}"
        return local_result
