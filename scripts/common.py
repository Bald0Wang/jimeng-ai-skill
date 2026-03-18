from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"


class ApiError(RuntimeError):
    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        self.code = code
        self.status = status
        super().__init__(message)


def get_api_key() -> str:
    for name in ("ARK_API_KEY", "VOLCENGINE_ARK_API_KEY"):
        value = os.getenv(name)
        if value:
            return value
    raise ApiError("MISSING_CREDENTIALS", "请设置环境变量 ARK_API_KEY")


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def task_hash(data: Mapping[str, Any]) -> str:
    return hashlib.md5(stable_json(data).encode("utf-8")).hexdigest()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def write_text(path: Path, data: str) -> None:
    path.write_text(data, encoding="utf-8")


def print_result(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(code: str, message: str, *, status: int | None = None) -> None:
    payload: dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if status is not None:
        payload["error"]["status"] = status
    print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
    raise SystemExit(1)


def _parse_error_payload(raw: bytes, status: int | None) -> ApiError:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return ApiError("HTTP_ERROR", "请求失败，且响应体为空", status=status)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ApiError("HTTP_ERROR", text, status=status)

    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return ApiError(
                str(error.get("code") or "API_ERROR"),
                str(error.get("message") or "接口调用失败"),
                status=status,
            )

        if "message" in data:
            return ApiError("API_ERROR", str(data["message"]), status=status)

    return ApiError("HTTP_ERROR", text, status=status)


def api_request(
    method: str,
    path: str,
    *,
    body: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
    timeout: int = 300,
    debug: bool = False,
) -> Any:
    api_key = get_api_key()
    url = f"{BASE_URL}{path}"
    if query:
        normalized: dict[str, Any] = {}
        for key, value in query.items():
            if value is None:
                continue
            normalized[key] = value
        if normalized:
            url = f"{url}?{urlencode(normalized, doseq=True)}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    payload_bytes: bytes | None = None
    if body is not None:
        payload_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if debug:
        print(f"[debug] {method.upper()} {url}", file=sys.stderr)
        if body is not None:
            print(json.dumps(body, ensure_ascii=False, indent=2), file=sys.stderr)

    request = Request(url=url, data=payload_bytes, headers=headers, method=method.upper())

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        raise _parse_error_payload(exc.read(), exc.code) from exc
    except URLError as exc:
        raise ApiError("NETWORK_ERROR", str(exc.reason)) from exc

    if not raw:
        return None

    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError("INVALID_RESPONSE", "接口返回了非 JSON 响应") from exc


def download_file(url: str, output_path: Path, timeout: int = 300) -> Path:
    ensure_dir(output_path.parent)
    request = Request(url, headers={"User-Agent": "jimeng-ai-skill/1.4.0"})
    with urlopen(request, timeout=timeout) as response:
        output_path.write_bytes(response.read())
    return output_path


def first_existing(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def image_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    candidates = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            candidates.append(path)
    return candidates
