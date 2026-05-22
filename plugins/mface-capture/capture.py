import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CAPTURED_SEGMENT_TYPES = {"mface", "image"}
DEFAULT_AUTO_STOP_SECONDS = 120
COMMAND_RESERVED_WORDS = {"状态", "开启", "关闭", "开", "关", "enable", "disable", "status"}

MFACE_KEYS = {
    "emoji_id",
    "emoji_package_id",
    "package_id",
    "key",
    "summary",
    "name",
    "emoji_type",
}

IMAGE_KEYS = {
    "file",
    "file_id",
    "summary",
    "sub_type",
    "type",
    "size",
    "width",
    "height",
}


class CaptureState:
    def __init__(
        self,
        enabled: bool = False,
        auto_stop_seconds: int = DEFAULT_AUTO_STOP_SECONDS,
        now: float = 0.0,
        label: str = "",
        source_origin: str = "",
    ):
        self.enabled = bool(enabled)
        self.auto_stop_seconds = normalize_auto_stop_seconds(auto_stop_seconds)
        self.expires_at = self._build_expires_at(now) if self.enabled else 0.0
        self.label = normalize_label(label)
        self.source_origin = normalize_source_origin(source_origin)

    def activate(
        self,
        now: float,
        label: str | None = None,
        source_origin: str | None = None,
    ) -> None:
        self.enabled = True
        self.expires_at = self._build_expires_at(now)
        if label is not None:
            self.label = normalize_label(label)
        if source_origin is not None:
            self.source_origin = normalize_source_origin(source_origin)

    def deactivate(self) -> None:
        self.enabled = False
        self.expires_at = 0.0
        self.label = ""
        self.source_origin = ""

    def is_active(self, now: float) -> bool:
        if not self.enabled:
            return False
        if self.expires_at and now >= self.expires_at:
            self.deactivate()
            return False
        return True

    def is_active_for(self, now: float, source_origin: str) -> bool:
        if not self.is_active(now):
            return False
        if not self.source_origin:
            return True
        return self.source_origin == normalize_source_origin(source_origin)

    def remaining_seconds(self, now: float) -> int:
        if not self.is_active(now):
            return 0
        if not self.expires_at:
            return 0
        return max(0, math.ceil(self.expires_at - now))

    def _build_expires_at(self, now: float) -> float:
        if self.auto_stop_seconds <= 0:
            return 0.0
        return float(now) + self.auto_stop_seconds


def normalize_auto_stop_seconds(value: Any) -> int:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return DEFAULT_AUTO_STOP_SECONDS
    return max(0, seconds)


def normalize_label(value: Any) -> str:
    return str(value or "").strip()[:40]


def normalize_source_origin(value: Any) -> str:
    return str(value or "").strip()[:200]


def parse_capture_label_command(message: str) -> str | None:
    text = str(message or "").strip()
    prefix = "/表情采集"
    if not text.startswith(prefix):
        return None
    label = text[len(prefix) :].strip()
    if not label or label in COMMAND_RESERVED_WORDS:
        return None
    return normalize_label(label)


def collect_records(
    raw_message: Any,
    message_type: str = "",
    capture_mface: bool = True,
    capture_image: bool = True,
    label: str = "",
) -> list[dict[str, Any]]:
    """Extract reusable mface/image metadata without chat text or sender IDs."""
    records: list[dict[str, Any]] = []
    allowed_types = set()
    if capture_mface:
        allowed_types.add("mface")
    if capture_image:
        allowed_types.add("image")

    for segment in _iter_segments(raw_message):
        segment_type = str(segment.get("type", "")).lower()
        if segment_type not in allowed_types:
            continue

        data = segment.get("data") or {}
        if not isinstance(data, dict):
            data = {}

        safe_data = _sanitize_segment_data(segment_type, data)
        if not safe_data:
            continue

        record = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "message_type": str(message_type or ""),
            "segment_type": segment_type,
            "data": safe_data,
        }
        normalized_label = normalize_label(label)
        if normalized_label:
            record["label"] = normalized_label
        record["fingerprint"] = _fingerprint(record)
        records.append(record)

    return records


def append_jsonl(path: str | Path, records: list[dict[str, Any]]) -> int:
    if not records:
        return 0

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            fh.write("\n")
    return len(records)


def build_download_jobs(
    raw_message: Any,
    records: list[dict[str, Any]],
    label: str = "",
) -> list[dict[str, str]]:
    segments = [
        segment
        for segment in _iter_segments(raw_message)
        if str(segment.get("type", "")).lower() in CAPTURED_SEGMENT_TYPES
    ]
    jobs: list[dict[str, str]] = []
    normalized_label = normalize_label(label) or "unlabeled"

    for idx, record in enumerate(records):
        if idx >= len(segments):
            break
        data = segments[idx].get("data") or {}
        if not isinstance(data, dict):
            continue
        url = data.get("url") or data.get("file_url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue

        filename = _build_local_image_filename(
            record.get("fingerprint") or f"{idx + 1:04d}",
            data,
            url,
        )
        relative_path = str(Path("images") / normalized_label / filename).replace(
            "\\", "/"
        )
        jobs.append(
            {
                "url": url,
                "relative_path": relative_path,
                "fingerprint": str(record.get("fingerprint") or ""),
            }
        )
    return jobs


def count_jsonl_lines(path: str | Path) -> int:
    target = Path(path)
    if not target.exists():
        return 0
    with target.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def _iter_segments(raw_message: Any):
    if raw_message is None:
        return

    if isinstance(raw_message, list):
        for item in raw_message:
            if isinstance(item, dict):
                yield item
        return

    if isinstance(raw_message, dict):
        message = raw_message.get("message")
        if isinstance(message, list):
            for item in message:
                if isinstance(item, dict):
                    yield item
            return
        if raw_message.get("type"):
            yield raw_message
        return

    message = getattr(raw_message, "message", None)
    if isinstance(message, list):
        for item in message:
            if isinstance(item, dict):
                yield item


def _sanitize_segment_data(segment_type: str, data: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = MFACE_KEYS if segment_type == "mface" else IMAGE_KEYS
    safe: dict[str, Any] = {}

    for key in allowed_keys:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value

    for url_key in ("url", "file_url"):
        value = data.get(url_key)
        if isinstance(value, str) and value:
            safe.update(_safe_url_parts(value))

    path_value = data.get("path")
    if isinstance(path_value, str) and path_value:
        safe["path_name"] = Path(path_value).name

    return safe


def _safe_url_parts(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    result: dict[str, str] = {}
    if parsed.netloc:
        result["url_host"] = parsed.netloc
    if parsed.path:
        parts = [part for part in parsed.path.split("/") if part]
        if parts:
            result["url_path_tail"] = "/".join(parts[-2:])
    return result


def _build_local_image_filename(
    fingerprint: str,
    data: dict[str, Any],
    url: str,
) -> str:
    ext = _guess_image_ext(data, url)
    return f"{_safe_filename_part(fingerprint)}{ext}"


def _guess_image_ext(data: dict[str, Any], url: str) -> str:
    candidates = [
        str(data.get("file") or ""),
        str(data.get("path") or ""),
        urlparse(url).path,
    ]
    for candidate in candidates:
        suffix = Path(candidate).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            return ".jpg" if suffix == ".jpeg" else suffix
    return ".bin"


def _safe_filename_part(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(value or "").strip())
    return safe[:80] or "image"


def _fingerprint(record: dict[str, Any]) -> str:
    body = {
        "message_type": record.get("message_type", ""),
        "segment_type": record.get("segment_type", ""),
        "data": record.get("data", {}),
    }
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
