from __future__ import annotations

import argparse
import cgi
import json
import mimetypes
import re
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
from .config import APP_HOST, APP_PORT, PUBLIC_DIR, REPORT_DIR, UPLOAD_DIR
from .extractors import build_information_package
from .knowledge import load_knowledge, summarize_counts
from .reporting import export_docx, export_pdf


def _safe_filename(filename: str) -> str:
    filename = Path(filename or "upload").name
    filename = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", filename)
    return filename or f"upload_{uuid.uuid4().hex}"


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    return str(value)


class DiagnosisHandler(BaseHTTPRequestHandler):
    server_version = "ApparelDiagnosis/0.1"

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

    def _send_static(self, request_path: str) -> None:
        rel = "index.html" if request_path in {"", "/"} else unquote(request_path.lstrip("/"))
        path = (PUBLIC_DIR / rel).resolve()
        if PUBLIC_DIR.resolve() not in path.parents and path != PUBLIC_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        self._send_file(path)

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
                self._send_json({"ok": True, "knowledge": summarize_counts(knowledge)})
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
                self._send_file(report_path, "服装企业全链路经营诊断报告.docx")
            elif path.startswith("/api/report/") and path.endswith(".pdf"):
                run_id = path.split("/")[-1].removesuffix(".pdf")
                result = self._read_result(run_id)
                report_path = REPORT_DIR / run_id / "服装企业全链路经营诊断报告.pdf"
                export_pdf(result, report_path)
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

    def _handle_analyze(self) -> None:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json({"ok": False, "error": "请使用 multipart/form-data 上传文件"}, status=400)
            return

        run_id = uuid.uuid4().hex[:12]
        upload_dir = UPLOAD_DIR / run_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        fields = form["files"] if "files" in form else []
        if not isinstance(fields, list):
            fields = [fields]
        saved_paths: list[Path] = []
        for field in fields:
            if not getattr(field, "filename", None):
                continue
            filename = _safe_filename(field.filename)
            target = upload_dir / filename
            with target.open("wb") as fh:
                shutil.copyfileobj(field.file, fh)
            saved_paths.append(target)

        if not saved_paths:
            self._send_json({"ok": False, "error": "没有收到有效文件"}, status=400)
            return

        knowledge = load_knowledge()
        package = build_information_package(saved_paths)
        result = analyze_information(package, knowledge)
        result = enhance_with_ai(result, package, knowledge)
        result["run_id"] = run_id
        result["knowledge_counts"] = knowledge["counts"]
        result["uploaded_files"] = [path.name for path in saved_paths]
        result["manual_ai_prompt"] = build_manual_ai_prompt(result, package, knowledge)
        self._write_result(run_id, result)
        self._send_json({"ok": True, "run_id": run_id, "result": result})


def main() -> None:
    parser = argparse.ArgumentParser(description="服装企业经营诊断本地网页工具")
    parser.add_argument("--host", default=APP_HOST)
    parser.add_argument("--port", type=int, default=APP_PORT)
    args = parser.parse_args()
    for directory in [UPLOAD_DIR, REPORT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    knowledge = load_knowledge()
    print(f"诊断知识库已加载：{summarize_counts(knowledge)}")
    print(f"本地网页地址：http://{args.host}:{args.port}")
    server = ThreadingHTTPServer((args.host, args.port), DiagnosisHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
