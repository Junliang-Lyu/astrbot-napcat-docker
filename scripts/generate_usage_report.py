import argparse
import csv
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "data" / "data_v4.db"
DEFAULT_OUTPUT_PATH = BASE_DIR / "项目运行基线_v0.1" / "13_自动用量日报.csv"

FIELDNAMES = [
    "日期",
    "调用次数",
    "成功调用次数",
    "异常调用次数",
    "DeepSeek调用次数",
    "OpenAI调用次数",
    "其他调用次数",
    "DeepSeek输入Token",
    "DeepSeek缓存输入Token",
    "DeepSeek输出Token",
    "OpenAI输入Token",
    "OpenAI缓存输入Token",
    "OpenAI输出Token",
    "其他输入Token",
    "其他缓存输入Token",
    "其他输出Token",
    "估算DeepSeek费用USD",
    "估算OpenAI费用USD",
    "估算总费用USD",
    "备注",
]

DEEPSEEK_V4_FLASH_PRICES = {
    "input": Decimal("0.14"),
    "cached_input": Decimal("0.0028"),
    "output": Decimal("0.28"),
}

OPENAI_GPT_54_MINI_PRICES = {
    "input": Decimal("0.75"),
    "cached_input": Decimal("0.075"),
    "output": Decimal("4.50"),
}


@dataclass
class Totals:
    calls: int = 0
    completed: int = 0
    abnormal: int = 0
    input_other: int = 0
    input_cached: int = 0
    output: int = 0

    def add(self, status: str, input_other: int, input_cached: int, output: int) -> None:
        self.calls += 1
        if status == "completed":
            self.completed += 1
        else:
            self.abnormal += 1
        self.input_other += input_other
        self.input_cached += input_cached
        self.output += output


def _safe_int(value: object) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _cost_usd(input_other: int, input_cached: int, output: int, prices: dict[str, Decimal]) -> Decimal:
    million = Decimal(1_000_000)
    return (
        Decimal(input_other) / million * prices["input"]
        + Decimal(input_cached) / million * prices["cached_input"]
        + Decimal(output) / million * prices["output"]
    )


def _format_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.000001'))}"


def _provider_bucket(provider_id: str, provider_model: str) -> str:
    label = f"{provider_id} {provider_model}".lower()
    if "deepseek" in label:
        return "deepseek"
    if "openai" in label or "gpt-" in label:
        return "openai"
    return "other"


def build_daily_rows(db_path: Path) -> list[dict[str, str]]:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    by_day: dict[str, dict[str, Totals]] = defaultdict(
        lambda: {
            "all": Totals(),
            "deepseek": Totals(),
            "openai": Totals(),
            "other": Totals(),
            "deepseek_priced": Totals(),
            "openai_mini_priced": Totals(),
        }
    )
    unknown_models_by_day: dict[str, set[str]] = defaultdict(set)

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT
                substr(created_at, 1, 10) AS day,
                provider_id,
                provider_model,
                status,
                token_input_other,
                token_input_cached,
                token_output
            FROM provider_stats
            WHERE created_at IS NOT NULL
            ORDER BY day
            """
        )
        for row in rows:
            day = str(row["day"])
            provider_id = str(row["provider_id"] or "")
            provider_model = str(row["provider_model"] or "")
            status = str(row["status"] or "")
            input_other = _safe_int(row["token_input_other"])
            input_cached = _safe_int(row["token_input_cached"])
            output = _safe_int(row["token_output"])
            bucket = _provider_bucket(provider_id, provider_model)

            by_day[day]["all"].add(status, input_other, input_cached, output)
            by_day[day][bucket].add(status, input_other, input_cached, output)

            if provider_model == "deepseek-v4-flash" or provider_id == "deepseek/deepseek-v4-flash":
                by_day[day]["deepseek_priced"].add(status, input_other, input_cached, output)
            elif provider_model == "gpt-5.4-mini" or provider_id == "openai/gpt-5.4-mini":
                by_day[day]["openai_mini_priced"].add(status, input_other, input_cached, output)
            else:
                unknown_models_by_day[day].add(provider_id or provider_model or "unknown")
    finally:
        con.close()

    daily_rows: list[dict[str, str]] = []
    for day in sorted(by_day):
        totals = by_day[day]["all"]
        deepseek = by_day[day]["deepseek"]
        openai = by_day[day]["openai"]
        other = by_day[day]["other"]
        deepseek_priced = by_day[day]["deepseek_priced"]
        openai_mini_priced = by_day[day]["openai_mini_priced"]

        deepseek_cost = _cost_usd(
            deepseek_priced.input_other,
            deepseek_priced.input_cached,
            deepseek_priced.output,
            DEEPSEEK_V4_FLASH_PRICES,
        )
        openai_cost = _cost_usd(
            openai_mini_priced.input_other,
            openai_mini_priced.input_cached,
            openai_mini_priced.output,
            OPENAI_GPT_54_MINI_PRICES,
        )
        unknown_models = sorted(unknown_models_by_day.get(day, set()))
        notes = [
            "自动生成；只读 provider_stats，不读取聊天内容",
            "费用只估算 deepseek-v4-flash 与 gpt-5.4-mini",
        ]
        if unknown_models:
            notes.append("未计价模型: " + "; ".join(unknown_models))

        daily_rows.append(
            {
                "日期": day,
                "调用次数": str(totals.calls),
                "成功调用次数": str(totals.completed),
                "异常调用次数": str(totals.abnormal),
                "DeepSeek调用次数": str(deepseek.calls),
                "OpenAI调用次数": str(openai.calls),
                "其他调用次数": str(other.calls),
                "DeepSeek输入Token": str(deepseek.input_other),
                "DeepSeek缓存输入Token": str(deepseek.input_cached),
                "DeepSeek输出Token": str(deepseek.output),
                "OpenAI输入Token": str(openai.input_other),
                "OpenAI缓存输入Token": str(openai.input_cached),
                "OpenAI输出Token": str(openai.output),
                "其他输入Token": str(other.input_other),
                "其他缓存输入Token": str(other.input_cached),
                "其他输出Token": str(other.output),
                "估算DeepSeek费用USD": _format_money(deepseek_cost),
                "估算OpenAI费用USD": _format_money(openai_cost),
                "估算总费用USD": _format_money(deepseek_cost + openai_cost),
                "备注": "；".join(notes),
            }
        )
    return daily_rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a daily provider usage report from AstrBot data_v4.db."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="Path to data_v4.db")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_daily_rows(args.db)
    write_csv(rows, args.out)
    print(f"Generated {len(rows)} daily rows: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
