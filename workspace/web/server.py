#!/usr/bin/env python3
"""PhotoManager local web studio with asynchronous FFmpeg rendering."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import quote, unquote, urlsplit


WEB_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = WEB_ROOT / "static"
RUNTIME_ROOT = WEB_ROOT / "runtime" / "jobs"
WORKSPACE_ROOT = WEB_ROOT.parent
DEMO_ROOT = WORKSPACE_ROOT / "demo"
RENDER_SCRIPT = DEMO_ROOT / "render_demo.py"
SAMPLE_SOURCE = DEMO_ROOT / "60c75319dd1281fef34a4b2f96579cc2.mp4"
FONT_BOLD = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 1024 * 1024
SUPPORTED_EXTENSIONS = {".gif", ".mp4", ".mov", ".m4v", ".webm"}
VARIANTS = {"all", "motion-cover", "break-frame", "time-slices"}
OUTPUT_FORMATS = {"mp4", "gif", "both"}
QUALITIES = {"high", "standard"}
JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.RLock()
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="render-worker")


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def ffmpeg_path() -> str:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError(
            "未找到 FFmpeg。请使用 start.sh 启动，或安装 requirements.txt。"
        ) from exc


def access_urls(port: int) -> list[str]:
    addresses = {"127.0.0.1"}
    try:
        _, _, resolved = socket.gethostbyname_ex(socket.gethostname())
        addresses.update(address for address in resolved if not address.startswith("127."))
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    ordered = sorted(addresses, key=lambda item: item.startswith("127."))
    return [f"http://{address}:{port}/" for address in ordered]


def ensure_runtime() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)


def job_dir(job_id: str) -> Path:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise ApiError(HTTPStatus.NOT_FOUND, "任务不存在")
    return RUNTIME_ROOT / job_id


def write_job(job: dict[str, Any]) -> None:
    target = job_dir(job["id"]) / "job.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(target)


def update_job(job_id: str, **changes: Any) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS[job_id]
        job.update(changes)
        job["updated_at"] = utc_now()
        write_job(job)
        return dict(job)


def load_jobs() -> None:
    ensure_runtime()
    for metadata_file in RUNTIME_ROOT.glob("*/job.json"):
        try:
            job = json.loads(metadata_file.read_text(encoding="utf-8"))
            if not JOB_ID_PATTERN.fullmatch(str(job.get("id", ""))):
                continue
            if job.get("status") in {"queued", "running"}:
                job.update(
                    status="failed",
                    phase="上次运行被中断，可重新创建任务",
                    error="本地服务在渲染完成前停止",
                    updated_at=utc_now(),
                )
                write_job(job)
            JOBS[job["id"]] = job
        except (OSError, ValueError, TypeError):
            continue


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        key: job.get(key)
        for key in (
            "id",
            "status",
            "phase",
            "progress",
            "original_name",
            "source_type",
            "variant",
            "output_format",
            "quality",
            "created_at",
            "updated_at",
            "error",
            "outputs",
        )
    }


def validate_options(fields: dict[str, str]) -> tuple[str, str, str]:
    variant = fields.get("variant", "motion-cover")
    output_format = fields.get("output_format", "mp4")
    quality = fields.get("quality", "high")
    if variant not in VARIANTS:
        raise ApiError(HTTPStatus.BAD_REQUEST, "未知的杂志结构")
    if output_format not in OUTPUT_FORMATS:
        raise ApiError(HTTPStatus.BAD_REQUEST, "未知的输出格式")
    if quality not in QUALITIES:
        raise ApiError(HTTPStatus.BAD_REQUEST, "未知的清晰度选项")
    return variant, output_format, quality


def validate_source(filename: str, payload: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ApiError(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            "当前只支持 GIF、MP4、MOV、M4V 和 WebM",
        )
    if not payload:
        raise ApiError(HTTPStatus.BAD_REQUEST, "上传文件为空")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "文件不能超过 100 MB")
    if suffix == ".gif" and not payload.startswith((b"GIF87a", b"GIF89a")):
        raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "文件不是有效的 GIF")
    source_type = "gif" if suffix == ".gif" else "video"
    return suffix, source_type


def parse_multipart(
    content_type: str, content_length: int, stream: BinaryIO
) -> tuple[dict[str, str], str, bytes]:
    if "multipart/form-data" not in content_type:
        raise ApiError(HTTPStatus.BAD_REQUEST, "请求必须使用 multipart/form-data")
    if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "上传请求不能超过 101 MB")

    body = stream.read(content_length)
    envelope = (
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()
        + body
    )
    message = BytesParser(policy=policy.default).parsebytes(envelope)
    if not message.is_multipart():
        raise ApiError(HTTPStatus.BAD_REQUEST, "无法解析上传内容")

    fields: dict[str, str] = {}
    filename = ""
    file_payload = b""
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        field_name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True) or b""
        part_filename = part.get_filename()
        if field_name == "file" and part_filename:
            filename = Path(part_filename).name
            file_payload = payload
        elif field_name:
            fields[field_name] = payload.decode("utf-8", errors="replace").strip()

    if not filename:
        raise ApiError(HTTPStatus.BAD_REQUEST, "请选择一个 GIF 或视频文件")
    return fields, filename, file_payload


def create_job(
    source_payload: bytes,
    original_name: str,
    suffix: str,
    source_type: str,
    variant: str,
    output_format: str,
    quality: str,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex
    directory = job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=False)
    source_path = directory / f"source{suffix}"
    source_path.write_bytes(source_payload)
    timestamp = utc_now()
    job: dict[str, Any] = {
        "id": job_id,
        "status": "queued",
        "phase": "等待本地渲染器",
        "progress": 0,
        "original_name": original_name,
        "source_type": source_type,
        "source_path": str(source_path),
        "variant": variant,
        "output_format": output_format,
        "quality": quality,
        "created_at": timestamp,
        "updated_at": timestamp,
        "error": None,
        "outputs": [],
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
        write_job(job)
    EXECUTOR.submit(run_render_job, job_id)
    return public_job(job)


def expected_steps(variant: str, output_format: str) -> int:
    variant_count = 3 if variant == "all" else 1
    exports = 2
    if output_format in {"mp4", "both"}:
        exports += 1
    if output_format in {"gif", "both"}:
        exports += 1
    return variant_count * exports + (1 if variant == "all" else 0)


def output_label(filename: str) -> str:
    stem = Path(filename).stem
    variant_names = {
        "01_motion_cover": "先锋动态封面",
        "02_break_frame": "斜切破版",
        "03_time_slices": "三时态切片",
        "comparison": "三版封面对比",
    }
    return variant_names.get(stem, stem.replace("_", " "))


def collect_outputs(job_id: str, output_dir: Path) -> list[dict[str, Any]]:
    files = sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".mp4", ".gif", ".jpg"}
    )
    names = {path.name for path in files}
    outputs: list[dict[str, Any]] = []
    for path in files:
        suffix = path.suffix.lower()
        media_type = {".mp4": "video", ".gif": "gif", ".jpg": "cover"}[suffix]
        media_url = f"/media/{job_id}/{quote(path.name)}"
        item: dict[str, Any] = {
            "name": path.name,
            "label": output_label(path.name),
            "type": media_type,
            "bytes": path.stat().st_size,
            "url": media_url,
            "download_url": f"{media_url}?download=1",
        }
        poster_name = f"{path.stem}.jpg"
        if media_type == "video" and poster_name in names:
            item["poster_url"] = f"/media/{job_id}/{quote(poster_name)}"
        outputs.append(item)
    return outputs


def last_log_message(log_path: Path) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "渲染器未返回错误详情"
    useful = [line.strip() for line in lines if line.strip()]
    return "\n".join(useful[-8:])[-1200:] or "渲染失败"


def run_render_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = dict(JOBS[job_id])
    output_dir = job_dir(job_id) / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir(job_id) / "render.log"
    total_steps = expected_steps(job["variant"], job["output_format"])
    completed_steps = 0
    update_job(job_id, status="running", phase="检查素材并准备无损母版", progress=2)

    command = [
        sys.executable,
        str(RENDER_SCRIPT),
        "--source",
        job["source_path"],
        "--output-dir",
        str(output_dir),
        "--variant",
        job["variant"],
        "--format",
        job["output_format"],
        "--quality",
        job["quality"],
    ]
    environment = dict(os.environ)
    environment["PYTHONUNBUFFERED"] = "1"

    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                command,
                cwd=DEMO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )
            assert process.stdout is not None
            for line in process.stdout:
                log_file.write(line)
                log_file.flush()
                stripped = line.strip()
                if stripped.startswith("生成："):
                    completed_steps += 1
                    filename = stripped.removeprefix("生成：")
                    progress = min(95, 4 + int(completed_steps / total_steps * 91))
                    update_job(
                        job_id,
                        phase=f"正在生成 {filename}",
                        progress=progress,
                    )
            return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(last_log_message(log_path))

        outputs = collect_outputs(job_id, output_dir)
        if not outputs:
            raise RuntimeError("渲染完成但没有找到输出文件")
        update_job(
            job_id,
            status="completed",
            phase="生成完成，可直接预览或保存",
            progress=100,
            outputs=outputs,
            error=None,
        )
    except Exception as exc:  # Worker boundary: persist a user-visible failure.
        update_job(
            job_id,
            status="failed",
            phase="生成失败",
            error=str(exc)[-1500:],
        )


def resolve_under(root: Path, requested: str) -> Path:
    candidate = (root / unquote(requested).lstrip("/")).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ApiError(HTTPStatus.NOT_FOUND, "文件不存在") from exc
    if not candidate.is_file():
        raise ApiError(HTTPStatus.NOT_FOUND, "文件不存在")
    return candidate


class PhotoManagerHandler(BaseHTTPRequestHandler):
    server_version = "PhotoManagerLocal/0.1"

    def log_message(self, format_string: str, *args: object) -> None:
        sys.stderr.write(
            f"[{self.log_date_time_string()}] {format_string % args}\n"
        )

    def do_GET(self) -> None:  # noqa: N802
        self._handle_get(send_body=True)

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle_get(send_body=False)

    def do_POST(self) -> None:  # noqa: N802
        try:
            path = urlsplit(self.path).path
            if path == "/api/jobs":
                self._create_uploaded_job()
                return
            if path == "/api/jobs/sample":
                self._create_sample_job()
                return
            raise ApiError(HTTPStatus.NOT_FOUND, "接口不存在")
        except ApiError as exc:
            self._send_json({"error": exc.message}, status=exc.status)
        except Exception as exc:
            self._send_json(
                {"error": f"本地服务发生错误：{exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _handle_get(self, send_body: bool) -> None:
        try:
            parsed = urlsplit(self.path)
            path = parsed.path
            if path == "/api/health":
                self._send_json(
                    {
                        "status": "ok",
                        "ffmpeg": Path(ffmpeg_path()).name,
                        "fonts": FONT_BOLD.is_file() and FONT_REGULAR.is_file(),
                        "max_upload_bytes": MAX_UPLOAD_BYTES,
                        "access_urls": access_urls(self.server.server_port),
                    },
                    send_body=send_body,
                )
                return
            if path == "/api/jobs":
                with JOBS_LOCK:
                    jobs = sorted(
                        (public_job(job) for job in JOBS.values()),
                        key=lambda item: item["created_at"] or "",
                        reverse=True,
                    )[:12]
                self._send_json({"jobs": jobs}, send_body=send_body)
                return
            if path.startswith("/api/jobs/"):
                requested_id = path.removeprefix("/api/jobs/")
                if not JOB_ID_PATTERN.fullmatch(requested_id):
                    raise ApiError(HTTPStatus.NOT_FOUND, "任务不存在")
                with JOBS_LOCK:
                    job = JOBS.get(requested_id)
                    if job is None:
                        raise ApiError(HTTPStatus.NOT_FOUND, "任务不存在")
                    payload = public_job(job)
                self._send_json(payload, send_body=send_body)
                return
            if path.startswith("/media/"):
                pieces = path.removeprefix("/media/").split("/", 1)
                if len(pieces) != 2:
                    raise ApiError(HTTPStatus.NOT_FOUND, "文件不存在")
                output_root = job_dir(pieces[0]) / "outputs"
                file_path = resolve_under(output_root, pieces[1])
                self._send_file(
                    file_path,
                    send_body=send_body,
                    download=parsed.query == "download=1",
                )
                return
            if path.startswith("/demo/"):
                file_path = resolve_under(DEMO_ROOT, path.removeprefix("/demo/"))
                self._send_file(file_path, send_body=send_body)
                return

            requested = "index.html" if path == "/" else path.lstrip("/")
            file_path = resolve_under(STATIC_ROOT, requested)
            self._send_file(file_path, send_body=send_body)
        except ApiError as exc:
            self._send_json(
                {"error": exc.message}, status=exc.status, send_body=send_body
            )
        except Exception as exc:
            self._send_json(
                {"error": f"本地服务发生错误：{exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                send_body=send_body,
            )

    def _create_uploaded_job(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Content-Length 无效") from exc
        fields, filename, payload = parse_multipart(
            self.headers.get("Content-Type", ""), content_length, self.rfile
        )
        variant, output_format, quality = validate_options(fields)
        suffix, source_type = validate_source(filename, payload)
        job = create_job(
            payload,
            filename,
            suffix,
            source_type,
            variant,
            output_format,
            quality,
        )
        self._send_json(job, status=HTTPStatus.ACCEPTED)

    def _create_sample_job(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "Content-Length 无效") from exc
        if content_length < 0 or content_length > 16 * 1024:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "请求过大")
        try:
            fields = json.loads(self.rfile.read(content_length) or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "JSON 请求无效") from exc
        if not isinstance(fields, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "JSON 请求无效")
        variant, output_format, quality = validate_options(
            {str(key): str(value) for key, value in fields.items()}
        )
        if not SAMPLE_SOURCE.is_file():
            raise ApiError(HTTPStatus.NOT_FOUND, "示例视频不存在")
        payload = SAMPLE_SOURCE.read_bytes()
        job = create_job(
            payload,
            SAMPLE_SOURCE.name,
            SAMPLE_SOURCE.suffix.lower(),
            "video",
            variant,
            output_format,
            quality,
        )
        self._send_json(job, status=HTTPStatus.ACCEPTED)

    def _base_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' blob: data:; "
            "media-src 'self' blob:; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; object-src 'none'; base-uri 'none'",
        )

    def _send_json(
        self,
        payload: Any,
        status: int = HTTPStatus.OK,
        send_body: bool = True,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._base_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if send_body:
            self.wfile.write(body)

    def _send_file(
        self, file_path: Path, send_body: bool = True, download: bool = False
    ) -> None:
        file_size = file_path.stat().st_size
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        start = 0
        end = file_size - 1
        status = HTTPStatus.OK
        range_header = self.headers.get("Range")
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                raise ApiError(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, "Range 无效")
            first, last = match.groups()
            if first:
                start = int(first)
                end = int(last) if last else end
            elif last:
                suffix_length = int(last)
                start = max(0, file_size - suffix_length)
            if start >= file_size or start > end:
                raise ApiError(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, "Range 超出文件")
            end = min(end, file_size - 1)
            status = HTTPStatus.PARTIAL_CONTENT

        length = max(0, end - start + 1)
        self.send_response(status)
        self._base_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        if download:
            self.send_header(
                "Content-Disposition",
                f"attachment; filename*=UTF-8''{quote(file_path.name)}",
            )
        self.end_headers()
        if not send_body or length == 0:
            return
        with file_path.open("rb") as source:
            source.seek(start)
            remaining = length
            while remaining:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_jobs()
    missing = [
        str(path)
        for path in (RENDER_SCRIPT, SAMPLE_SOURCE, FONT_BOLD, FONT_REGULAR)
        if not path.is_file()
    ]
    if missing:
        raise SystemExit("缺少运行资源：\n" + "\n".join(missing))
    try:
        ffmpeg = ffmpeg_path()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    server = ThreadingHTTPServer((args.host, args.port), PhotoManagerHandler)
    server.daemon_threads = True
    print("PhotoManager 本地网站：", flush=True)
    for url in access_urls(args.port):
        label = "手机访问" if "127.0.0.1" not in url else "本机访问"
        print(f"  {label}：{url}", flush=True)
    print(f"FFmpeg：{ffmpeg}", flush=True)
    print(
        "仅在可信局域网使用，按 Ctrl+C 停止。素材与结果只保存在 workspace/web/runtime/。",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        EXECUTOR.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
