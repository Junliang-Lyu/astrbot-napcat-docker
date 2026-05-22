import csv
import json
from datetime import datetime
from pathlib import Path


CAPTURE_FILE = Path("data/plugin_data/astrbot_plugin_mface_capture/mface_captures.jsonl")
OUTPUT_FILE = Path("data/plugin_data/astrbot_plugin_mface_capture/mface_label_manifest.csv")


LINE_LABELS = [
    (1, 6, "开心", "from_log_command"),
    (7, 10, "生气", "from_log_command"),
    (11, 15, "害羞", "from_log_command"),
    (16, 25, "感谢", "from_log_command"),
    (26, 32, "疑惑", "user_confirmed_order"),
    (33, 36, "伤心", "user_confirmed_order"),
    (37, 45, "赞同", "from_log_command"),
]


def label_for_line(line_no: int) -> tuple[str, str]:
    for start, end, label, source in LINE_LABELS:
        if start <= line_no <= end:
            return label, source
    return "", "unmapped"


def load_records(path: Path) -> list[dict]:
    records = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def main() -> int:
    records = load_records(CAPTURE_FILE)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "line_no",
                "captured_at",
                "segment_type",
                "fingerprint",
                "label",
                "label_source",
                "note",
            ],
        )
        writer.writeheader()
        for line_no, record in enumerate(records, start=1):
            label = record.get("label") or ""
            source = "record_label" if label else ""
            if not label:
                label, source = label_for_line(line_no)
            writer.writerow(
                {
                    "line_no": line_no,
                    "captured_at": record.get("captured_at", ""),
                    "segment_type": record.get("segment_type", ""),
                    "fingerprint": record.get("fingerprint", ""),
                    "label": label,
                    "label_source": source,
                    "note": "" if label else "needs_manual_label",
                }
            )
    print(f"generated={OUTPUT_FILE}")
    print(f"records={len(records)}")
    print(f"generated_at={datetime.now().isoformat(timespec='seconds')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
