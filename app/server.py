from __future__ import annotations

import argparse
import cgi
import json
import mimetypes
import shutil
import sys
import traceback
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

from .ai_client import build_manual_ai_prompt, enhance_with_ai
from .analyzer import analyze_information
from .config import APP_HOST, APP_PORT, DIAGNOSIS_PUBLIC_DIR, PUBLIC_DIR, REPORT_DIR, UPLOAD_DIR
from .data_center import (
    build_information_package_from_materials,
    list_materials,
    list_reports,
    record_report,
    record_report_export,
    store_uploaded_fields,
)
from .knowledge import load_knowledge, summarize_counts
from .reporting import export_docx, export_pdf


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _values_as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


def _parse_bool(value) -> bool:
    if isinstance(value, list):
        return any(_parse_bool(item) for item in value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "all", "全部"}


def _parse_material_ids(value) -> list[str]:
    values = _values_as_list(value)
    material_ids: list[str] = []
    for item in values:
        item = item.strip()
        if not item:
            continue
        if item.startswith("["):
            try:
                parsed = json.loads(item)
                material_ids.extend(str(entry).strip() for entry in parsed if str(entry).strip())
                continue
            except Exception:
                pass
        material_ids.extend(part.strip() for part in item.split(",") if part.strip())
    seen: set[str] = set()
    result: list[str] = []
    for material_id in material_ids:
        if material_id not in seen:
            seen.add(material_id)
            result.append(material_id)
    return result


class PlatformHandler(BaseHTTPRequestHandler):
    server_version = "ApparelGrowthSystem/0.2"

    def log_message(self, format: str, *args):  # noqa: A003
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, download_name: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        if download_name:
            encoded = quote(download_name)
            self.send_header("Content-Disposition", f"attachment; filename=report; filename*=UTF-8''{encoded}")
        self.end_headers()
        with path.open("rb") as fh:
            shutil.copyfileobj(fh, self.wfile)

    def _send_static_file(self, root: Path, rel: str) -> None:
        root = root.resolve()
        path = (root / rel).resolve()
        if root not in path.parents and path != root:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        self._send_file(path)

    def _send_static(self, request_path: str) -> None:
        if request_path in {"", "/"}:
            self._send_static_file(PUBLIC_DIR, "index.html")
            return

        if request_path in {"/modules/01-enterprise-diagnosis", "/modules/01-enterprise-diagnosis/"}:
            self._send_static_file(DIAGNOSIS_PUBLIC_DIR, "index.html")
            return

        if request_path.startswith("/modules/01-enterprise-diagnosis/"):
            rel = unquote(request_path.removeprefix("/modules/01-enterprise-diagnosis/"))
            self._send_static_file(DIAGNOSIS_PUBLIC_DIR, rel or "index.html")
            return

        rel = unquote(request_path.lstrip("/"))
        self._send_static_file(PUBLIC_DIR, rel)

    def _read_result(self, run_id: str) -> dict:
        path = REPORT_DIR / run_id / "result.json"
        if not path.exists():
            raise FileNotFoundError(f"未找到分析结果：{run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_result(self, run_id: str, result: dict) -> Path:
        result_dir = REPORT_DIR / run_id
        result_dir.mkdir(parents=True, exist_ok=True)
        path = result_dir / "result.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/health":
                knowledge = load_knowledge()
                materials = list_materials()
                self._send_json(
                    {
                        "ok": True,
                        "knowledge": summarize_counts(knowledge),
                        "data_center": materials["counts"],
                    }
                )
            elif path == "/api/materials":
                self._send_json(list_materials())
            elif path == "/api/reports":
                self._send_json(list_reports())
            elif path == "/api/knowledge":
                self._send_json(load_knowledge())
            elif path.startswith("/api/result/"):
                run_id = path.split("/")[-1]
                self._send_json(self._read_result(run_id))
            elif path.startswith("/api/report/") and path.endswith(".docx"):
                run_id = path.split("/")[-1].removesuffix(".docx")
                result = self._read_result(run_id)
                report_path = REPORT_DIR / run_id / "服装企业全链路经营诊断报告.docx"
                export_docx(result, report_path)
                record_report_export(run_id, "docx", report_path)
                self._send_file(report_path, "服装企业全链路经营诊断报告.docx")
            elif path.startswith("/api/report/") and path.endswith(".pdf"):
                run_id = path.split("/")[-1].removesuffix(".pdf")
                result = self._read_result(run_id)
                report_path = REPORT_DIR / run_id / "服装企业全链路经营诊断报告.pdf"
                export_pdf(result, report_path)
                record_report_export(run_id, "pdf", report_path)
                self._send_file(report_path, "服装企业全链路经营诊断报告.pdf")
            else:
                self._send_static(path)
        except Exception as exc:
            traceback.print_exc()
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/analyze":
                self._handle_analyze()
            elif path == "/api/materials":
                self._handle_material_upload()
            elif path.startswith("/api/result/"):
                run_id = path.split("/")[-1]
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                result = payload.get("result")
                if not isinstance(result, dict):
                    self._send_json({"ok": False, "error": "缺少 result 对象"}, status=400)
                    return
                self._write_result(run_id, result)
                self._send_json({"ok": True, "run_id": run_id})
            else:
                self._send_json({"ok": False, "error": "未知接口"}, status=404)
        except Exception as exc:
            traceback.print_exc()
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _upload_fields_from_form(self, form: cgi.FieldStorage) -> list:
        fields = form["files"] if "files" in form else []
        if not isinstance(fields, list):
            fields = [fields]
        return fields

    def _handle_material_upload(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json({"ok": False, "error": "请使用 multipart/form-data 上传文件"}, status=400)
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        source_module = str(form.getvalue("source_module") or "data-center")
        materials = store_uploaded_fields(self._upload_fields_from_form(form), source_module=source_module)
        if not materials:
            self._send_json({"ok": False, "error": "没有收到有效文件"}, status=400)
            return
        self._send_json({"ok": True, "materials": materials, "data_center": list_materials()["counts"]})

    def _handle_analyze(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        new_materials: list[dict] = []
        material_ids: list[str] = []
        use_all_materials = False

        if "multipart/form-data" in content_type:
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
            new_materials = store_uploaded_fields(self._upload_fields_from_form(form), source_module="enterprise-diagnosis")
            material_ids = _parse_material_ids(form.getvalue("material_ids"))
            material_ids.extend(record["id"] for record in new_materials if record.get("extract_status") == "ready")
            use_all_materials = _parse_bool(form.getvalue("use_all_materials"))
        elif "application/json" in content_type:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            material_ids = _parse_material_ids(payload.get("material_ids"))
            use_all_materials = _parse_bool(payload.get("use_all_materials"))
        else:
            self._send_json({"ok": False, "error": "请上传文件，或传入资料中心 material_ids"}, status=400)
            return

        if not material_ids and not use_all_materials:
            self._send_json({"ok": False, "error": "请先上传资料，或从资料中心选择资料"}, status=400)
            return

        package = build_information_package_from_materials(material_ids, use_all_materials=use_all_materials)
        if not package["files"]:
            self._send_json({"ok": False, "error": "选中的资料还没有可用识别结果"}, status=400)
            return

        knowledge = load_knowledge()
        result = analyze_information(package, knowledge)
        result = enhance_with_ai(result, package, knowledge)
        run_id = uuid.uuid4().hex[:12]
        result["run_id"] = run_id
        result["knowledge_counts"] = knowledge["counts"]
        result["material_ids"] = package["material_ids"]
        result["new_materials"] = new_materials
        result["uploaded_files"] = [file["filename"] for file in package["files"]]
        result["data_center"] = {
            "material_ids": package["material_ids"],
            "new_material_count": len(new_materials),
            "used_all_materials": use_all_materials,
        }
        result["manual_ai_prompt"] = build_manual_ai_prompt(result, package, knowledge)
        self._write_result(run_id, result)
        record_report(
            run_id=run_id,
            module_id="enterprise-diagnosis",
            title="服装企业全链路经营诊断报告",
            result=result,
            material_ids=package["material_ids"],
        )
        self._send_json({"ok": True, "run_id": run_id, "result": result})


def main() -> None:
    parser = argparse.ArgumentParser(description="服装企业经营管理提效工具")
    parser.add_argument("--host", default=APP_HOST)
    parser.add_argument("--port", type=int, default=APP_PORT)
    args = parser.parse_args()
    for directory in [UPLOAD_DIR, REPORT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    knowledge = load_knowledge()
    print(f"诊断知识库已加载：{summarize_counts(knowledge)}")
    print(f"总工作台地址：http://{args.host}:{args.port}")
    print(f"经营诊断模块：http://{args.host}:{args.port}/modules/01-enterprise-diagnosis/")
    server = ThreadingHTTPServer((args.host, args.port), PlatformHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
